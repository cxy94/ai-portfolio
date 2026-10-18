import csv, weekpath  # weekpath：统一解析data/路径
DATA = weekpath.data_path("生词表.csv")

# ① 读取生词csv
def load_words(path=DATA):
    # with自动关闭文件，utf-8防止Windows中文乱码
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ② 按HSK等级筛选（列表推导式写法）
def filter_by_level(words, level="4"):
    return [w for w in words
            if str(w["HSK等级"]) == str(level)]

# ③ 统计词性分布
def count_by_pos(words):
    d = {}
    for w in words:
        d[w["词性"]] = d.get(w["词性"], 0) + 1
    return d

# ④ 扩展功能：生成挖空填空题
def gen_exercises(words, out=None):
    # 输出文件固定在项目根目录
    out = out or weekpath.root_path("填空练习.txt")
    with open(out, "w", encoding="utf-8") as f:
        for w in words:
            # 词汇挖空为____
            f.write(f"用____造一个句子。（{w['词性']}）\n")

if __name__ == "__main__":
    word_list = load_words()
    hsk4 = filter_by_level(word_list, "4")
    pos_count = count_by_pos(hsk4)
    gen_exercises(hsk4)
    print("词性统计结果：", pos_count)


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
① 增加 encoding="utf-8"：Windows 系统读写中文文件缺少编码声明会出现乱码。
② 将原生 open () 改为 with open () 上下文写法：自动释放文件资源，不需要手动 close，更安全。
③ 接入 weekpath 路径工具：统一数据文件和输出文件路径，脚本在任意位置都能正常运行。
④（作业 1 补充）把循环筛选改为列表推导式：精简代码，是 Python 列表处理的推荐简洁写法。
