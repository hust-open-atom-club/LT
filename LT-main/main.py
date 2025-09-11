from src.lt.translator import Translator
from argparse import ArgumentParser

argparse = ArgumentParser()
argparse.add_argument("path")
argparse.add_argument("target")
argparse.add_argument("model")

args = argparse.parse_args()

path = args.path
target = args.target
model = args.model

translator = Translator(path=path, target=target, model=model)

translator.translate()
