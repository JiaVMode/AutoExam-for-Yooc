import json

def number_to_letter(num_str):
    """将数字字符串转换为字母（0→A, 1→B, 2→C, 3→D...）"""
    try:
        num = int(num_str)
        return chr(65 + num)  # 65是'A'的ASCII码
    except:
        return num_str

def convert_answers_to_letters(question_bank):
    """将题库中的数字答案转换为字母答案"""
    converted_bank = {}
    
    for subject_id, subject_data in question_bank.items():
        converted_data = subject_data.copy()
        
        # 转换答案
        if "correct_answer" in converted_data:
            original_answer = converted_data["correct_answer"]
            letter_answer = [number_to_letter(ans) for ans in original_answer]
            
            # 保存转换后的答案
            converted_data["correct_answer_letters"] = letter_answer
            converted_data["correct_answer_numbers"] = original_answer
            
            # 如果是单选题，也保存单个字母
            if converted_data.get("type") == "choice" and len(letter_answer) == 1:
                converted_data["answer"] = letter_answer[0]
            # 如果是多选题，保存字母组合
            elif converted_data.get("type") == "multiplechoice":
                converted_data["answer"] = "".join(sorted(letter_answer))
            else:
                converted_data["answer"] = ", ".join(letter_answer)
        
        converted_bank[subject_id] = converted_data
    
    return converted_bank

def save_to_readable_format(converted_bank, filename="question_bank_readable.txt"):
    """保存为易读的文本格式"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("题库答案对照表（字母版）\n")
        f.write("=" * 80 + "\n\n")
        
        # 按题目类型分组
        choice_questions = []
        multiplechoice_questions = []
        completion_questions = []
        
        for subject_id, data in converted_bank.items():
            if data.get("type") == "choice":
                choice_questions.append((subject_id, data))
            elif data.get("type") == "multiplechoice":
                multiplechoice_questions.append((subject_id, data))
            else:
                completion_questions.append((subject_id, data))
        
        # 输出单选题
        if choice_questions:
            f.write("【单选题】\n")
            f.write("-" * 80 + "\n")
            for subject_id, data in sorted(choice_questions):
                title = data.get("title", "")[:60]
                answer = data.get("answer", "")
                numbers = data.get("correct_answer_numbers", [])
                f.write(f"ID: {subject_id}\n")
                f.write(f"题目: {title}...\n")
                f.write(f"答案: {answer} (原始值: {numbers})\n")
                f.write("\n")
        
        # 输出多选题
        if multiplechoice_questions:
            f.write("\n" + "=" * 80 + "\n")
            f.write("【多选题】\n")
            f.write("-" * 80 + "\n")
            for subject_id, data in sorted(multiplechoice_questions):
                title = data.get("title", "")[:60]
                answer = data.get("answer", "")
                numbers = data.get("correct_answer_numbers", [])
                f.write(f"ID: {subject_id}\n")
                f.write(f"题目: {title}...\n")
                f.write(f"答案: {answer} (原始值: {numbers})\n")
                f.write("\n")
        
        # 输出填空题
        if completion_questions:
            f.write("\n" + "=" * 80 + "\n")
            f.write("【填空题】\n")
            f.write("-" * 80 + "\n")
            for subject_id, data in sorted(completion_questions):
                title = data.get("title", "")[:60]
                answer = data.get("correct_answer_numbers", [])
                f.write(f"ID: {subject_id}\n")
                f.write(f"题目: {title}...\n")
                f.write(f"答案: {answer}\n")
                f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write(f"总计: {len(converted_bank)} 道题\n")
        f.write(f"  - 单选题: {len(choice_questions)} 题\n")
        f.write(f"  - 多选题: {len(multiplechoice_questions)} 题\n")
        f.write(f"  - 填空题: {len(completion_questions)} 题\n")
        f.write("=" * 80 + "\n")

def main():
    # 读取原始题库
    print("正在读取题库...")
    with open('question_bank.json', 'r', encoding='utf-8') as f:
        question_bank = json.load(f)
    
    print(f"题库共有 {len(question_bank)} 道题")
    
    # 转换答案
    print("正在转换答案格式...")
    converted_bank = convert_answers_to_letters(question_bank)
    
    # 保存为易读文本格式
    txt_filename = "question_bank_readable.txt"
    save_to_readable_format(converted_bank, txt_filename)
    print(f"[OK] 已保存文本格式: {txt_filename}")
    
    print("\n生成完成！")
    print(f"\n生成的文件:")
    print(f"  - {txt_filename} - 详细文本格式（按题型分类，字母答案）")

if __name__ == "__main__":
    main()

