## 1. 任务与提示词
要做什么：读生词表CSV→筛HSK4→生成挖空填空题
我写的提示词：
角色：Python教学助手
任务：写脚本读取生词表csv，筛选HSK等级为4的词语，生成填空题，把词汇挖空变成____；统计词性分布；输出txt文件；仅使用标准库，每行代码加上注释，csv字段名是【词汇、词性、HSK等级】

## 2. AI初版代码
```python
import csv

def load_words(path):
    f = open(path)
    reader = csv.DictReader(f)
    return list(reader)

def filter_by_level(words, level="4"):
    res = []
    for w in words:
        if w["HSK等级"] == level:
            res.append(w)
    return res

def gen_fill_exercise(words, out_file):
    f = open(out_file, "w")
    for w in words:
        line = f"请填空：用 ____ 造句子。（{w['词性']}）\n"
        f.write(line)
    f.close()

if __name__ == "__main__":
    all_words = load_words("data/生词表.csv")
    hsk4_words = filter_by_level(all_words)
    gen_fill_exercise(hsk4_words, "fill_exercise.txt")
