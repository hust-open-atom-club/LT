import abc
import os

from openai import OpenAI
from pathlib import Path

base_prompt = """You are a translator and an expert in both Chinese and English. You will receive a text snippet from 
a .rst file. The file is also written in English. As a translation tool, you will solely return the same string in 
Chinese without losing or amending the original formatting. Your translations are accurate, aiming not to deviate 
from the original structure, content, writing style and tone. Along with the translation process, you must obey rules 
as follows: 
1. Your translation should restrict each line within 80 English characters, one Chinese character equals 
two English characters. 
2. Try your best to keep the same length for each line. 
3. Keep consistency with original text.
4. Do NOT translate code block or specific word.
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
    
Translation should looks like this:

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


class BaseAgent:
    def __init__(self, repo, target):
        self.messages = []
        self.prompt = base_prompt
        self.target = target
        self.client = OpenAI(
            base_url="http://localhost:8000/v1",
            api_key="NA"
        )
        self.repo = repo
        self.path = Path(f"/tmp/LT/{repo}")
        self.__init_repo()
        self.output_dir = self.path / "translations/zh_CN" / target
        if not self.output_dir.exists():
            self.output_dir.mkdir(exist_ok=True, parents=True)

    def __init_repo(self):
        if not self.path.exists():
            # if repo not exists, clone it to /tmp/LT
            os.system(f"git clone https://mirrors.hust.edu.cn/git/lwn.git {self.path}")
            os.system(f"cd {self.path} && git checkout docs-next")
        self.path = self.path / "Documentation"
        if self.target not in self.path.iterdir():
            raise ValueError(f"No such target: {self.target}")
        target = self.path / self.target
        if target.is_dir():
            self.target = list(target.glob("**/*.rst"))
        else:
            self.target = target
        os.system("make cleandocs && make htmldocs")

    def start(self):
        p

    @abc.abstractmethod
    def call(self, input_text):
        raise NotImplementedError

    @abc.abstractmethod
    @property
    def name(self):
        raise NotImplementedError
