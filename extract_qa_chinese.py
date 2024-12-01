import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import json
import logging
import re
from typing import List, Dict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_epub(epub_path: str) -> epub.EpubBook:
    """读取EPUB文件"""
    try:
        book = epub.read_epub(epub_path)
        logging.info(f"成功读取EPUB文件: {epub_path}")
        return book
    except Exception as e:
        logging.error(f"读取EPUB文件失败: {str(e)}")
        raise

def is_content_item(item: ebooklib.epub.EpubItem) -> bool:
    """判断是否为内容项"""
    if item.get_type() == ebooklib.ITEM_DOCUMENT:
        filename = item.get_name().lower()
        if any(x in filename for x in ['nav', 'toc', 'content.opf', 'cover']):
            return False
        return True
    return False

def clean_text(text: str) -> str:
    """清理文本，删除多余的空白字符"""
    # 替换多个空白字符为单个空格
    text = re.sub(r'\s+', ' ', text)
    # 删除首尾空白
    return text.strip()

def extract_qa_from_html(html_content: str, file_name: str = "") -> List[Dict[str, str]]:
    """从HTML内容中提取问答对"""
    qa_pairs = []
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 查找所有可能的问题标签
        questions = soup.find_all(['h3', 'h2'], class_=lambda x: x and 
            ('bodycontent-second-title' in x or 'bodycontent-second-title1' in x))
        
        if not questions:
            logging.debug(f"在文件 {file_name} 中未找到问题标签")
            return []

        for q in questions:
            question_text = clean_text(q.get_text())
            
            # 跳过空问题
            if not question_text or len(question_text) < 2:
                continue
                
            answer_paragraphs = []
            current = q.next_sibling
            
            # 获取问题后面的所有段落，直到遇到下一个问题或特定标签
            while current:
                if current.name in ['h3', 'h2'] and isinstance(current.get('class', []), list) and \
                   any('bodycontent-second-title' in c for c in current.get('class', [])):
                    break
                    
                if current.name == 'p' and 'bodycontent-text' in current.get('class', []):
                    text = clean_text(current.get_text())
                    if text:
                        answer_paragraphs.append(text)
                current = current.next_sibling
            
            # 将所有段落合并为完整答案
            answer = '\n'.join(answer_paragraphs)
            
            if question_text and answer:
                qa_pairs.append({
                    "question": question_text,
                    "answer": answer
                })
                logging.debug(f"提取到问答对 - 问题: {question_text[:50]}...")

    except Exception as e:
        logging.error(f"处理HTML内容时出错 ({file_name}): {str(e)}")
        
    return qa_pairs

def extract_qa_from_epub(epub_path: str) -> List[Dict[str, str]]:
    """从EPUB中提取问答对"""
    book = read_epub(epub_path)
    all_qa_pairs = []
    processed_files = 0
    
    for item in book.get_items():
        if is_content_item(item):
            try:
                html_content = item.get_content().decode('utf-8')
                qa_pairs = extract_qa_from_html(html_content, item.get_name())
                if qa_pairs:
                    all_qa_pairs.extend(qa_pairs)
                processed_files += 1
                if processed_files % 10 == 0:
                    logging.info(f"已处理 {processed_files} 个文件，当前共提取 {len(all_qa_pairs)} 个问答对")
            except Exception as e:
                logging.error(f"处理文件失败 {item.get_name()}: {str(e)}")
                continue
    
    logging.info(f"处理完成，共处理 {processed_files} 个文件，提取 {len(all_qa_pairs)} 个问答对")
    return all_qa_pairs

def save_qa_to_json(qa_pairs: List[Dict[str, str]], output_file: str):
    """将问答对保存到JSON文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
        logging.info(f"成功保存 {len(qa_pairs)} 个问答对到文件: {output_file}")
    except Exception as e:
        logging.error(f"保存JSON文件失败: {str(e)}")
        raise

def main():
    try:
        epub_path = "十万个为什么--第六版-彩色图文本 (韩启德主编 [韩启德主编]) (Z-Library).epub"
        output_file = "qa_pairs_chinese.json"
        
        logging.info("开始提取问答对...")
        qa_pairs = extract_qa_from_epub(epub_path)
        
        if qa_pairs:
            save_qa_to_json(qa_pairs, output_file)
            logging.info("处理完成！")
        else:
            logging.warning("未提取到任何问答对")
            
    except Exception as e:
        logging.error(f"程序执行失败: {str(e)}")

if __name__ == "__main__":
    main()