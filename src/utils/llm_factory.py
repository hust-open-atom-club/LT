"""
LLM工厂 - 支持多种模型提供商
"""

import os
import json
from typing import Optional, Any, List, Dict, Union
from langchain_openai import ChatOpenAI
from langchain.llms.base import LLM
from pydantic import Field

from .config import config_manager


class QwenChatModel(LLM):
    """
    Qwen模型的LangChain兼容包装器 - 使用OpenAI SDK
    """
    
    model: str = Field(default="qwen-plus", description="模型名称")
    temperature: float = Field(default=0.1, description="生成的随机性")
    client: Any = Field(default=None, description="OpenAI客户端")
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True
    
    def __init__(self, model: str = "qwen-plus", temperature: float = 0.1, api_key: str = None, **kwargs):
        """
        初始化Qwen模型
        
        Args:
            model: 模型名称 (qwen-plus, qwen-max, qwen-turbo)
            temperature: 生成的随机性
            api_key: API密钥（可选，优先级高于配置文件）
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai>=1.0.0")
        
        # 获取API密钥配置
        qwen_config = config_manager.get_qwen_config(api_key=api_key)
        if not qwen_config['api_key']:
            raise ValueError("请在配置文件config.ini中设置qwen.api_key，或通过参数传递API密钥")
        
        # 使用OpenAI SDK创建客户端
        client = OpenAI(
            api_key=qwen_config['api_key'],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 调用父类初始化
        super().__init__(
            model=model,
            temperature=temperature,
            client=client,
            **kwargs
        )
    
    def _safe_format_messages(self, messages: Union[str, List, Any]) -> List[Dict[str, str]]:

        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]

        if hasattr(messages, 'format'):
            formatted_content = str(messages)
            return [{"role": "user", "content": formatted_content}]

        if isinstance(messages, list):
            formatted_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    role = getattr(msg, 'type', 'user')
                    if role == 'human':
                        role = 'user'
                    elif role == 'ai':
                        role = 'assistant'
                    elif role == 'system':
                        role = 'system'
                
                    content = msg.content
                    if isinstance(content, list):
                        content = ' '.join(str(item) for item in content)
                    
                    formatted_messages.append({"role": role, "content": str(content)})
                elif isinstance(msg, dict):
                    safe_msg = {}
                    for k, v in msg.items():
                        safe_msg[k] = str(v) if not isinstance(v, (str, int, float, bool)) else v
                    formatted_messages.append(safe_msg)
                else:
                    formatted_messages.append({"role": "user", "content": str(msg)})
            return formatted_messages
        
        return [{"role": "user", "content": str(messages)}]
    
    @property
    def _llm_type(self) -> str:
        """返回LLM类型"""
        return "qwen"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:

        try:
            # 调用Qwen
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                stop=stop,
                **kwargs
            )
            
            return completion.choices[0].message.content
                
        except Exception as e:
            raise Exception(f"Qwen模型调用出错: {str(e)}")
    
    def invoke(self, input, config=None, **kwargs):
        try:
            formatted_messages = self._safe_format_messages(input)
            
            # 调用Qwen API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=self.temperature,
                **kwargs
            )
            
            response_text = completion.choices[0].message.content
            return response_text
                
        except Exception as e:
            raise Exception(f"Qwen模型调用出错: {str(e)}")


class QwenResponse:
    
    def __init__(self, content: str):
        self.content = content
        self.text = content 
        self.generations = [self] 
    
    def __str__(self):
        return self.content
    
    def __repr__(self):
        return f"QwenResponse(content='{self.content[:50]}...')"
    
    @property
    def generation_info(self):
        return {}
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.content == other
        elif hasattr(other, 'content'):
            return self.content == other.content
        return False


class LLMFactory:
    
    @staticmethod
    def get_supported_models() -> Dict[str, List[str]]:
        """获取支持的模型列表"""
        return {
            "openai": [
                "gpt-4",
                "gpt-3.5-turbo-16k"
            ],
            "qwen": [
                "qwen-plus",
                "qwen-max", 
                "qwen-turbo"
            ]
        }
    
    @staticmethod
    def create_llm(model_name: str, 
                   provider: str = "auto", 
                   temperature: float = 0.1,
                   openai_api_key: Optional[str] = None,
                   qwen_api_key: Optional[str] = None,
                   **kwargs):

        if provider == "auto":
            supported_models = LLMFactory.get_supported_models()
            for provider_name, models in supported_models.items():
                if model_name in models:
                    provider = provider_name
                    break
            
            if provider == "auto":
                raise ValueError(f"无法自动识别模型 {model_name} 的提供商")

        if provider == "openai":
            return LLMFactory._create_openai_llm(
                model_name, temperature, openai_api_key, **kwargs
            )
        elif provider == "qwen":
            return LLMFactory._create_qwen_llm(
                model_name, temperature, qwen_api_key, **kwargs
            )
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    @staticmethod
    def _create_openai_llm(model_name: str, temperature: float, api_key: Optional[str] = None, **kwargs):

        openai_config = config_manager.get_openai_config(api_key=api_key)
        
        if not openai_config['api_key']:
            raise ValueError("在配置文件config.ini中设置openai.api_key")
        
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=openai_config['api_key'],
            openai_api_base=openai_config.get('base_url'),
            **kwargs
        )
    
    @staticmethod  
    def _create_qwen_llm(model_name: str, temperature: float, api_key: Optional[str] = None, **kwargs):
        
        return QwenChatModel(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            **kwargs
        )