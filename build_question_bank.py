import json
import os
import requests
import urllib3
import bs4

def initialize():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with open('config.json', 'r') as read_config:
        config = json.load(read_config)
    return config

def get_review_data(config):
    """从复习页面获取题目和正确答案"""
    
    # 获取examuserId
    setting_get = requests.get(
        'https://exambackend.yooc.me/api/exam/setting/get',
        params={
            "userId": config.get("userId", ""),
            "examId": config["examId"],
            "token": config["user_token"],
            "yibanId": config.get("yibanId", ""),
        },
        verify=False
    )
    
    if setting_get.status_code != 200:
        print("无法获取考试设置")
        return None
    
    try:
        exam_data = setting_get.json()["data"]
        examuserId = exam_data.get("examuserId", "")
        
        if not examuserId:
            print("未找到examuserId，可能还没有完成过考试")
            return None
        
        print(f"找到examuserId: {examuserId}")
        
        # 使用exam/answer/get API获取完整答案数据
        answer_get = requests.get(
            'https://exambackend.yooc.me/api/exam/answer/get',
            params={
                "examuserId": examuserId,
                "token": config["user_token"],
                "yibanId": config.get("yibanId", ""),
            },
            verify=False
        )
        
        if answer_get.status_code == 200:
            print("成功获取答案数据")
            return answer_get.json()
        else:
            print(f"获取答案失败: {answer_get.status_code}")
            return None
            
    except Exception as e:
        print(f"获取数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_answers_from_review(review_data, show_details=True):
    """解析复习数据，提取题目ID和正确答案"""
    question_bank = {}
    
    if not review_data or "data" not in review_data:
        print("没有找到复习数据")
        return question_bank
    
    # 加载现有题库，用于标识新题目
    existing_bank = load_existing_question_bank()
    
    # 获取答案数据 (answers 包含是否正确的标记)
    answers_dict = {}
    if "answers" in review_data:
        for answer_item in review_data["answers"]:
            for subject_id, answer_data in answer_item.items():
                # answer_data 格式: [{"1": ["1"]}, 1]  最后的1表示正确，-1表示错误
                user_answer_obj = answer_data[0]
                is_correct = answer_data[1]
                answers_dict[subject_id] = {
                    "user_answer_obj": user_answer_obj,
                    "is_correct": is_correct
                }
    
    data = review_data["data"]
    correct_count = 0
    wrong_count = 0
    
    # 遍历所有section
    for section in data:
        if "subjects" not in section:
            continue
            
        for subject in section["subjects"]:
            subject_id = str(subject["subjectId"])
            subject_type = subject["type"]  # choice, multiplechoice, completion
            
            # 提取题目文本（去除HTML标签）
            title_html = subject.get("title", "")
            if isinstance(title_html, list) and len(title_html) > 0:
                title_html = title_html[0]
            soup = bs4.BeautifulSoup(str(title_html), 'html.parser')
            title_text = soup.get_text(strip=True)
            
            # 解密正确答案
            import yooc_crypto
            encrypted_answer = subject.get("answer", "")
            yibanId = config.get("yibanId", "")
            
            try:
                decrypted = yooc_crypto.decrypt(encrypted_answer, yibanId)
                correct_answer = json.loads(decrypted)
            except:
                correct_answer = []
            
            # 获取用户答案和是否正确
            answer_info = answers_dict.get(subject_id, {})
            is_correct = answer_info.get("is_correct", 0) == 1
            
            # 保存到题库
            question_bank[subject_id] = {
                "title": title_text[:100],  # 只保存前100个字符作为标识
                "type": subject_type,
                "correct_answer": correct_answer,
            }
            
            # 打印信息
            status = "[对]" if is_correct else "[错]"
            is_new = subject_id not in existing_bank
            new_tag = "[新]" if is_new else "[旧]"
            
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1
            
            if show_details:
                print(f"{status} {new_tag} ID:{subject_id} [{subject_type:15}] 正确答案:{correct_answer}")
                if title_text:
                    print(f"   题目: {title_text[:80]}...")
    
    print(f"\n统计: 答对 {correct_count} 题, 答错 {wrong_count} 题, 总计 {correct_count + wrong_count} 题")
    
    return question_bank

def load_existing_question_bank(filename="question_bank.json"):
    """加载现有题库"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_question_bank(question_bank, filename="question_bank.json"):
    """保存题库到文件（增量更新模式）"""
    # 加载现有题库
    existing_bank = load_existing_question_bank(filename)
    
    # 统计信息
    new_count = 0
    updated_count = 0
    
    # 合并题库
    for subject_id, subject_data in question_bank.items():
        if subject_id not in existing_bank:
            # 新题目
            existing_bank[subject_id] = subject_data
            new_count += 1
        else:
            # 已存在的题目，检查是否需要更新
            if existing_bank[subject_id] != subject_data:
                existing_bank[subject_id] = subject_data
                updated_count += 1
    
    # 保存合并后的题库
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_bank, f, ensure_ascii=False, indent=2)
    
    print(f"\n题库更新完成:")
    print(f"  - 题库文件: {filename}")
    print(f"  - 总题目数: {len(existing_bank)} 题")
    print(f"  - 新增题目: {new_count} 题")
    print(f"  - 更新题目: {updated_count} 题")
    print(f"  - 保持不变: {len(existing_bank) - new_count - updated_count} 题")

def main():
    global config
    print("开始构建题库...")
    config = initialize()
    
    # 如果配置中没有userId和yibanId，需要先获取
    if "userId" not in config or "yibanId" not in config:
        print("配置文件中缺少userId或yibanId，正在获取...")
        info_get = requests.get(
            'https://www.yooc.me/mobile/dashboard/my_info',
            cookies={
                "user_token": config["user_token"],
                "sessionid": config["sessionid"],
            },
            verify=False
        )
        info_soup = bs4.BeautifulSoup(info_get.text, 'html.parser')
        info_list = info_soup.find_all('span', class_='cc')
        config["userId"] = info_list[2].text
        config["yibanId"] = info_list[3].text
        print(f"userId: {config['userId']}, yibanId: {config['yibanId']}\n")
    
    # 获取复习数据
    review_data = get_review_data(config)
    
    if review_data:
        # 解析答案
        question_bank = parse_answers_from_review(review_data)
        
        # 保存题库
        if question_bank:
            save_question_bank(question_bank)
        else:
            print("未能提取到任何题目")
    else:
        print("无法获取复习数据")

if __name__ == "__main__":
    main()

