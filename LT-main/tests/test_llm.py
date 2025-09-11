from openai import OpenAI 
import re
Translator_prompt = """
```
# Role: Translator and Formatting Expert

## Profile
- author: MarkLee 
- version: 1.0
- language: Bilingual (English and Chinese)
- description: You are a translation expert specializing in precise translations between English and Chinese. You will receive English text fragments from .rst files and translate them into Chinese, while maintaining the original format. Your translations are accurate and strive to match the structure, content, writing style, and tone of the original text. Strict rules must be followed throughout the translation process.
## Constrains
1. No more than 80 characters per line, with one Chinese character counting as two English characters
2. Output nothing other than the translated content
3. Do not translate code, and do not enclose code blocks
4. Ensure the original format remains unchanged

## Rules
1. Proper nouns must maintain correct capitalization
2. Ensure complete code strings and English names are not split across lines

## Workflows
1. Read the content of the .rst file provided by the user
2. Standardize the document content according to the specified rules, one by one

Here is an example:
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

Formatting_prompt = """
# Role: 中文文档规范助手

## Profile
- author: MarkLee 
- version: 1.0
- language: 中文
- description: You will receive Chinese text fragments from .rst files and formate them ，确保文档格式、空格使用、专有名词大小写以及代码完整性等符合标准。

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
6. 保证完整的代码字符串和英文名称不被分割跨行。

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
def assistant_message(content):
    return {
        "role": "system",
        "content": content
    }
def user_message(content):
    return {
        "role": "user",
        "content": content
    }
# 将原文分段，每段限制在一定字符数以内，避免大模型处理过长文本
def split_text(text, max_length=3000):
    # 正则表达式匹配代码块和标题
    code_block_pattern = re.compile(r'::\n\n(?: {4}.*\n)+')
    heading_pattern = re.compile(r'^(=+|-+|~+)$', re.MULTILINE)

    chunks = []
    current_chunk = ""
    
    paragraphs = re.split(r'(\n\n)', text)  # 使用空行进行分割，保留分割符

    for i, paragraph in enumerate(paragraphs):
        # 跳过空行
        if not paragraph.strip():
            continue

        # 检查是否是代码块或标题
        is_code_block = code_block_pattern.search(paragraph)
        is_heading = heading_pattern.search(paragraph)
        
        # 确保不会在代码块或标题处分割
        if len(current_chunk) + len(paragraph) <= max_length or is_code_block or is_heading:
            current_chunk += paragraph
        else:
            chunks.append(current_chunk)
            current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)

    return chunks
client = OpenAI(
    api_key="58e58c9a47c2f8f8fe4698520283a6ed.TFzgfEA0w0OK8PLa",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
) 
# client = OpenAI(
#     base_url='http://222.20.126.129:11434/v1/',

#     # required but ignored
#     api_key='ollama',
# )
original_text = open("/home/marklee/repo/LT/lwn/Documentation/dev-tools/gdb-kernel-debugging.rst", "r").read()
# 分割原始文本
text_chunks = split_text(original_text)
# 创建一个列表存储翻译后的文本
translated_text = []

# 创建翻译消息模板
Translator_prompt = assistant_message(Translator_prompt)

for chunk in text_chunks:
    Translate_messages = [Translator_prompt]
    Translate_messages.append({"role": "user", "content": chunk})

    # 调用大模型翻译
    Translate_completion = client.chat.completions.create(
        model="glm-4-0520",  
        messages=Translate_messages,
        top_p=0.7,
        temperature=0.9
    )
    
    # 将翻译后的内容添加到列表中
    translated_text.append(Translate_completion.choices[0].message.content)

# 将所有翻译后的文本整合
final_translation = "\n\n".join(translated_text)
# Translate_messages = [Translator_prompt]
# Translate_messages.append(user_message(original_text))
# Translate_completion = client.chat.completions.create(
#         model="glm-4-0520",  
#         messages=Translate_messages,
#         top_p=0.7,
#         temperature=0.9
#     )

# with open("./gdb-kernel-debugging.rst", "w+", encoding="utf-8") as file:
#     file.write(Translate_completion.choices[0].message.content)
# 将翻译后的内容写入到新文件中
with open("./gdb-kernel-debugging.rst", "w+", encoding="utf-8") as file:
    file.write(final_translation)

print("Translation complete and written to gdb-kernel-debugging.rst")

# Formatting_messages = [assistant_message(Formatting_prompt)]
# Formatting_messages.append(user_message(Translate_completion.choices[0].message.content))

# Formatting_completion = client.chat.completions.create(
#     model="glm-4",  
#     messages=Formatting_messages,
#     top_p=0.7,
#     temperature=0.9
#  ) 
# with open("./gdb-kernel-debugging.rst","a+",encoding="utf-8") as file:
#     file.write(Formatting_completion.choices[0].message.content) 