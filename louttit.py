#!/bin/env -S python

import argparse
import json
import os
import random
import sys
import re

MEM_FILE = '.quiz_memory.json'

# Load or init memory
if os.path.exists(MEM_FILE):
    with open(MEM_FILE, 'r', encoding='utf-8') as f:
        memory = json.load(f)
else:
    memory = {}  # key -> {"asked": int, "correct": int, "meaning": str}

# Parse args
def parse_args():
    p = argparse.ArgumentParser(description='Selik 詞彙拼寫測驗')
    p.add_argument('files', nargs='*', help='Selik 詞彙文件，若不指定則測驗過去錯詞')
    return p.parse_args()

# Parse vocabulary files
def load_vocab(files):
    vocab = {}
    # 匹配格式: 序號. [Selik 單詞 (可包含空格)] [意思]
    pattern = re.compile(r'^\s*\d+\.\s*([A-Za-z ]+)\s+(.+)$')
    for fn in files:
        try:
            with open(fn, encoding='utf-8') as f:
                for line in f:
                    m = pattern.match(line)
                    if not m:
                        continue
                    word = m.group(1).strip()
                    meaning = m.group(2).strip()
                    vocab[word] = meaning
        except FileNotFoundError:
            print(f"Warning: 無法打開文件 {fn}")
    return vocab

# Select quiz list
def select_words(vocab, memory, limit=None):
    items = []
    if vocab:
        for w, meaning in vocab.items():
            stats = memory.get(w, {'asked': 0, 'correct': 0})
            asked, correct = stats['asked'], stats['correct']
            err = 1.0 - (correct/asked if asked>0 else 0)
            items.append((err, w, meaning))
    else:
        for w, stats in memory.items():
            asked, correct = stats['asked'], stats['correct']
            if asked>0 and correct<asked:
                meaning = stats.get('meaning', '')
                items.append((1.0 - correct/asked, w, meaning))
    items.sort(reverse=True, key=lambda x: x[0])
    if limit:
        items = items[:limit]
    return [(w, m) for _, w, m in items]

# Quiz loop
def quiz_loop(words):
    print("按 'q' 隨時保存並退出\n")
    for w, m in words:
        prompt = f"意思：{m}\n拼寫: "
        ans = input(prompt).strip()
        if ans.lower() == 'q':
            break
        stats = memory.setdefault(w, {'asked': 0, 'correct': 0, 'meaning': m})
        stats['asked'] += 1
        if ans == w:
            stats['correct'] += 1
            print("✔ 正確!\n")
        else:
            print(f"✘ 錯誤，正確拼寫：{w}\n")

# Save memory

def save_memory():
    with open(MEM_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    print(f"已保存進度到 {MEM_FILE}")


def main():
    args = parse_args()
    if args.files:
        vocab = load_vocab(args.files)
        if not vocab:
            print("未在指定文件中找到有效詞條。退出。")
            return
        words = select_words(vocab, memory)
    else:
        words = select_words({}, memory)
        if not words:
            print("無過去錯詞記錄。請傳入詞彙文件開始測驗。")
            return
    quiz_loop(words)
    save_memory()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n中斷，保存進度...")
        save_memory()
        sys.exit(0)
