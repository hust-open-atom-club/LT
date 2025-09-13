# 优化后的base_prompt，供全局使用
base_prompt = """
# 你在翻译时，输出内容必须以如下Markdown元数据头部开头：
# ---
# status: translated
# title: 填写译文标题
# author: 填写原文作者
# collector: 填写你的GitHub ID
# collected_date: 填写原文收集日期（如20240912）
# translator: 填写你的GitHub ID
# translated_date: 填写当前日期（如20240912）
# link: 填写原文链接
# ---
# 之后再输出翻译正文内容。
# 优化后的base_prompt，供全局使用
base_prompt = """
import os
import subprocess

from openai import OpenAI
from pathlib import Path

"""
# Role: Translator and Formatting Expert

## Profile
- author: MarkLee
- version: 1.0
- language: Bilingual (English and Chinese)
- description: You are a translation expert specializing in precise translations between English and Chinese. You will receive English text fragments from .rst files and translate them into Chinese, while maintaining the original format. Your translations are accurate and strive to match the structure, content, writing style, and tone of the original text. Strict rules must be followed throughout the translation process.

## Skills
1. Bilingual translation expert (English-Chinese), capable of precise translations with consistency.
2. Skilled at handling technical documents, ensuring that format, code blocks, and specific terms remain untranslated.
3. Expertise in controlling line length, ensuring that the Chinese translation matches the English length as closely as possible, with no more than 80 characters per line.
4. Maintains complete alignment in content, format, and tone between the source and translated text.

## Rules
1. During translation, limit the number of characters per line to 80 English characters, with one Chinese character counting as two English characters.
2. Ensure each line is as uniform in length as possible.
3. Maintain consistency in content, style, format, and tone with the original text.
4. Do not translate code blocks or specific terms.
5. Guarantee translation accuracy without altering or omitting the original content.

## Workflows
1. Receive and analyze the content structure of the English text.
2. Begin line-by-line translation, ensuring the number of characters per line follows the specified rules.
3. Check the translated text to ensure format and consistency, keeping code blocks and specific terms unchanged.
4. Compare the translated text with the original to ensure complete alignment in content and style.
5. Output the translated Chinese text, retaining the original format and code.

## Example:
Origin text:

===========  
Hello World  
===========  

This is a hello world code in C language

.. ::code: c  
    #include<stdio.h>  
    
    int main() {  
        printf("Hello World");  
        return 0;  
    }

Translation should look like this:

==========  
你好，世界  
==========  

这是一个用 C 语言编写的你好世界代码。

.. ::code: c  
    #include<stdio.h>  
    
    int main() {  
        printf("Hello World");  
        return 0;  
    }
"""


class Translator:
    def __init__(self,
                 path,
                 target,
                 model):
        self.model = model
        self.path = Path(path)
        self.target = target
        self.prompt = base_prompt
        self.messages = [{"role": "system", "content": self.prompt}]
        self.client = OpenAI(
            base_url="http://localhost:8000/v1",
            api_key="NA"
        )
        # 如果是本地tests目录，跳过repo初始化，直接处理文件
        if str(self.path).endswith('tests'):
            self.target = [self.path / target]
            self.output_dir = self.path / "translations/zh_CN"
            if not self.output_dir.exists():
                self.output_dir.mkdir(exist_ok=True, parents=True)
        else:
            self.__init_repo()
            os.chdir(self.path / target)
            self.output_dir = self.path / "translations/zh_CN" / target
            if not self.output_dir.exists():
                self.output_dir.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def assistant_message(content):
        return {
            "role": "assistant",
            "content": content
        }

    @staticmethod
    def user_message(content):
        return {
            "role": "user",
            "content": content
        }

    def __init_repo(self):
        """
        __init_repo init the kernel repo and change self.path to target directory
        after called, self.target is a list of .rst file
        :return:
        """
        if not self.path.exists():
            # if repo not exists, clone it to /tmp/LT
            os.system(f"git clone https://mirrors.hust.edu.cn/git/lwn.git {self.path}")
        os.system(f"cd {self.path} && git checkout docs-next")
        self.path = self.path / "Documentation"
        self.target = self.path / self.target
        if self.target not in self.path.iterdir():
            raise ValueError(f"No such target: {self.target}")
        if self.target.is_dir():
            self.target = [target.name for target in (self.target.glob("**/*.rst"))]
        # os.system("cd lwn && make cleandocs && make htmldocs")

    def save(self, target, translation):
        with open(self.output_dir / target, "w+", encoding="utf-8") as f:
            f.write(translation)

    def translate(self):
        """
        翻译→格式校对→输出md
        """
        formatting_prompt = """
# Role: 中文文档规范助手

## Profile
- author: MarkLee
- version: 1.0
- language: 中文
- description: 一个帮助用户根据指定规则规范中文文档的助手，确保文档格式、空格使用、专有名词大小写以及代码完整性等符合标准。

## Skills
1. 能够识别并添加中英文单词之间的空格。
2. 能够识别并添加中文字符与数字之间的空格。
3. 避免在全角标点符号和其他字符之间添加多余空格。
4. 正确处理专有名词的大小写。
5. 在链接之间添加适当的空格。
6. 自动添加许可证声明和免责声明到文档的末尾。
7. 避免在行内中断完整的代码字符串或英文专有名词。

## Rules
1. 中英文单词之间添加空格。
2. 中文字符与数字之间添加空格。
3. 全角标点符号和其他字符之间不加空格。
4. 专有名词保持正确的大小写。
5. 链接之间添加空格。
6. 在文档末尾始终包含以下内容：
   .. SPDX-License-Identifier: GPL-2.0
   .. include:: ../disclaimer-zh_CN.rst
7. 保证完整的代码字符串和英文名称不被分割跨行。

## Workflows
1. 读取用户提供的 .rst 文件内容。
2. 根据指定规则逐条规范文档内容：
   - 检查中英文之间的空格并添加。
   - 检查中文与数字之间的空格并添加。
   - 检查并确保全角标点符号和其他字符之间没有多余空格。
   - 检查并修正专有名词的大小写。
   - 确保链接之间有空格。
   - 确保完整代码字符串或英文专有名词不被分割。
3. 在文档末尾添加许可证声明和免责声明。
4. 输出修正后的文档。
"""
        def split_text(text, max_length=3000):
            """将长文本按段落分块，避免切断代码块和标题"""
            import re
            code_block_pattern = re.compile(r'```[\s\S]*?```|::[\s\S]*?(?=\n\S|$)', re.MULTILINE)
            blocks = []
            last = 0
            for m in code_block_pattern.finditer(text):
                if m.start() > last:
                    blocks.extend([b for b in text[last:m.start()].split('\n\n') if b.strip()])
                blocks.append(m.group())
                last = m.end()
            if last < len(text):
                blocks.extend([b for b in text[last:].split('\n\n') if b.strip()])
            # 合并小块，保证每块不超过max_length
            merged, buf = [], ''
            for b in blocks:
                if len(buf) + len(b) < max_length:
                    buf += ('\n\n' if buf else '') + b
                else:
                    if buf:
                        merged.append(buf)
                    buf = b
            if buf:
                merged.append(buf)
            return merged

        for target in self.target:
            original_text = open(target, "r", encoding="utf-8").read()
            chunks = split_text(original_text, max_length=3000)
            translated_chunks = []
            head = ''
            for idx, chunk in enumerate(chunks):
                self.messages = [self.assistant_message(self.prompt)]
                # 只在首块加元数据头部提示
                if idx == 0:
                    self.messages.append(self.user_message(chunk))
                else:
                    # 后续块去除prompt头部，防止重复
                    self.messages.append(self.user_message(chunk))
                resp = self.client.chat.completions.create(
                    messages=self.messages,
                    model=self.model,
                )
                translation = resp.choices[0].message.content
                if idx == 0:
                    # 提取首块头部
                    import re
                    m = re.match(r'(-{3,}|# ?-+)[\s\S]*?(-{3,}|# ?-+)', translation)
                    if m:
                        head = translation[:m.end()]
                        body = translation[m.end():].lstrip('\n')
                        translated_chunks.append(body)
                    else:
                        # 没有头部也保留原文
                        translated_chunks.append(translation)
                else:
                    translated_chunks.append(translation)
            full_translation = '\n\n'.join(translated_chunks)
            # 校对/格式规范
            proof_messages = [self.assistant_message(formatting_prompt)]
            proof_messages.append(self.user_message(full_translation))
            proof_resp = self.client.chat.completions.create(
                messages=proof_messages,
                model=self.model,
            )
            proofed = proof_resp.choices[0].message.content
            # 校对后如头部丢失则自动补回
            if head and not proofed.lstrip().startswith(head[:10]):
                proofed = head + '\n' + proofed.lstrip('\n')
            # 输出md格式
            md_path = self.output_dir / (Path(target).stem + ".md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(proofed)
            print(f"[✓] {md_path} written.")

    @staticmethod
    def __check_error(target):
        # make htmldocs 2 >& 1
        p = subprocess.run("make htmldocs 2>&1", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            raise RuntimeError(f"Error while compiling: {p.stderr}")
        if target in p.stdout:
            print("Error about translation format")
            return False
        return True
