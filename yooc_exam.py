import json
import random
import time
import os

import bs4
import requests
import urllib3

import to_wrong
import yooc_crypto


def initialize():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with open('config.json', 'r', encoding='utf-8') as read_config:
        config = json.load(read_config)
    return config

def load_question_bank():
    """加载题库"""
    if os.path.exists('question_bank.json'):
        try:
            with open('question_bank.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_user_info(info):
    info_get = requests.get(
        'https://www.yooc.me/mobile/dashboard/my_info',
        cookies = {
            "user_token": config["user_token"], 
            "sessionid": config["sessionid"], 
        },
        verify = False
    )
    info_soup = bs4.BeautifulSoup(info_get.text, 'html.parser')
    info_list = info_soup.find_all('span', class_ = 'cc')
    info["name"] = info_list[1].text
    info["userId"] = info_list[2].text
    info["yibanId"] = info_list[3].text
    return info

def reset_exam(info):
    setting_get = requests.get(
        'https://exambackend.yooc.me/api/exam/setting/get', 
        params = {
            "userId": info["userId"], 
            "examId": info["examId"], 
            "token": info["user_token"], 
            "yibanId": info["yibanId"], 
        }, 
        verify = False
    )
    try:
        examuserId = setting_get.json()["data"]["examuserId"]
    except:
        examuserId = ''
        pass
    else:
        requests.post(
            'https://exambackend.yooc.me/api/exam/repeat/action', 
            params = {
                "token": info["user_token"], 
                "yibanId": info["yibanId"], 
            }, 
            data = {
                "examuserId": examuserId, 
                "examId": info["examId"], 
            }, 
            verify = False
        )
    return examuserId

def create_exam(info):
    requests.post(
        'https://exambackend.yooc.me/api/exam/start/action',
        params = {
            "token": info["user_token"], 
            "yibanId": info["yibanId"], 
        }, 
        data = {
            "userId": info["userId"], 
            "examId": info["examId"], 
        }, 
        verify = False
    )

def get_examuserId(info):
    setting_get = requests.get(
        'https://exambackend.yooc.me/api/exam/setting/get', 
        params = {
            "userId": info["userId"], 
            "examId": info["examId"], 
            "token": info["user_token"], 
            "yibanId": info["yibanId"], 
        }, 
        verify = False
    )
    examuserId=setting_get.json()["data"]["examuserId"]
    return examuserId

def get_paper(info, question_bank):
    paper_get = requests.get(
        'https://exambackend.yooc.me/api/exam/paper/get', 
        params = {
            "examuserId": info["examuserId"], 
            "token": info["user_token"], 
            "yibanId": info["yibanId"], 
        }, 
        verify = False
    )
    data = paper_get.json()["data"]
    paper = []
    for section in data:
        subjects = section["subjects"]
        for subject in subjects:
            plain = yooc_crypto.decrypt(subject["answer"], info["yibanId"])
            answer = json.loads(plain)
            subject_id = str(subject["subjectId"])
            
            fixed_subject = {
                "id": subject_id, 
                "type": subject["type"], # choice, multiplechoice, completion
                "inputs": int(subject["inputs"]), 
                "points": int(subject["points"]), 
                "answer": answer, 
                "count": 1,
                "title": subject.get("title", ""),  # 保存题目标题用于匹配
            }
            if fixed_subject["type"] != 'completion':
                fixed_subject["options"] = len(subject["option"])
            
            # 如果题库中有这道题的答案，使用题库答案
            if subject_id in question_bank and "correct_answer" in question_bank[subject_id]:
                fixed_subject["answer"] = question_bank[subject_id]["correct_answer"]
                print(f"使用题库答案: 题目ID {subject_id}")
            
            paper.append(fixed_subject)
    return paper

def change_answer(subject):
    subject["count"] = -1
    if subject["type"] == 'completion':
        subject["answer"] = to_wrong.to_wrong(subject["answer"])
    else:
        while True:
            random_answer = [str(random.randint(0,subject["options"]-1))]
            if subject["answer"] != random_answer:
                subject["answer"] = random_answer
                break
    return subject

def get_answer(paper, accuary):
    full_score = 0
    num = 0
    for item in paper:
        choiced_answer = []
        full_score += item["points"]
        
        # 处理多选题、单选题和填空题
        for filling in item["answer"]: # multiople answer to single answer
            if isinstance(filling, list):
                # 多选题：使用题库答案（已经是列表格式）
                if item["type"] == 'multiplechoice':
                    choiced_answer = filling
                else:
                    choiced_answer.append(filling[0])
            else:
                choiced_answer.append(filling)
        
        # 打印调试信息
        if item["type"] == 'choice':
            print(f"单选题 ID {item['id']}: 答案 {choiced_answer}")
        elif item["type"] == 'multiplechoice':
            print(f"多选题 ID {item['id']}: 答案 {choiced_answer}")
        
        item["answer"] = choiced_answer
        paper[num] = item
        num += 1
    target_score = full_score * accuary/100
    now_score = full_score
    
    while True:
        candidate = []
        num = 0
        for item in paper:
            if item["count"] == 1 and now_score - item["points"] >= target_score:
                candidate.append({
                    "item": item, 
                    "num": num, 
                })
            num += 1
        if not candidate:
            break
        choice = random.choice(candidate)
        paper[choice["num"]] = change_answer(choice["item"])
        now_score -= choice["item"]["points"]
    
    answer = {}
    for item in paper:
        embed = {}
        if item["inputs"] == 1:
            embed["1"] = item["answer"]
        else:
            for num in range(len(item["answer"])):
                embed[str(num+1)] = [item["answer"][num]]
        answer[item["id"]] = [embed, int(item["count"])]
    return {
        "answer": answer, 
        "score": now_score, 
    }

def wait(timespan, noise):
    sleep_time = timespan*60
    sleep_time *= random.uniform(1-noise,1+noise)
    time.sleep(sleep_time)

def submit(info, answer):
    created_answer = json.dumps(answer["answer"], ensure_ascii = False, sort_keys = True)
    created_answer = '"' + created_answer.replace('"', '\\"') + '"'
    score = yooc_crypto.encrypt_score(answer["score"], info["yibanId"])

    requests.post(
        'https://exambackend.yooc.me/api/exam/submit/action', 
        params = {
            "token": info["user_token"], 
            "yibanId": info["yibanId"], 
        }, 
        data = {
            "answer": created_answer, 
            "score": score, 
            "examuserId": str(info["examuserId"]), 
        }, 
        verify = False
    )

def check_result(info):
    check_get = requests.get(
        'https://exambackend.yooc.me/api/exam/result/get', 
        params = {
            "userId": info["userId"], 
            "token": info["user_token"], 
            "yibanId": info["yibanId"], 
            "examId": info["examId"], 
        }, 
        verify = False
    )
    result = check_get.json()
    score = result["data"]["score"]
    duration = result["data"]["duration"]
    print(f'{info["name"]} finished,')
    print(f'    used {duration//60} min {duration%60} s, ')
    print(f'    the score is {score}. ')


noise = 0.1 # noise of sleep time
config = initialize()
question_bank = load_question_bank()
print(f"已加载题库，共 {len(question_bank)} 道题目")
info = get_user_info(config)
info["examuserId"] = reset_exam(info)
create_exam(info)
info["examuserId"] = get_examuserId(info)
paper = get_paper(info, question_bank)
answer = get_answer(paper, info["accuracy"])
wait(info["time"], noise)
submit(info, answer)
check_result(info)
