
# from peft import AutoPeftModelForCausalLM, AutoModelForCausalLM
from transformers import AutoTokenizer, AutoModelForCausalLM

from argparse import ArgumentParser
import json
import logging
from tqdm import tqdm
from typing import List, Union


def _get_args():
    parser = ArgumentParser()
    parser.add_argument("-c", "--checkpoint-path", type=str, default='checkpoints/Qwen-1_8B-Chat_finetune_20241207',
                        help="Checkpoint name or path")
    args = parser.parse_args()
    return args

class PromptAttributeExtractor2_5():
    def __init__(
            self,
            model_dir='checkpoints/qwen2_5-1_5b-20241217-merged'):
        '''
        Init the class to extract structured attributes from the prompt(in English) using LLM.
        @param model_dir: the directory of the finetuned LLM model.
        @return: None
        '''
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_dir, # path to the output directory
            torch_dtype="auto",
            device_map="auto"
        ).eval()

    def extract_attribute(
            self,
            args: Union[str, List[str]],
    ) -> Union[dict, List[dict]]:
        '''
        Extract structured attributes from the prompt(in English) using LLM.
        @param args: the input prompt(in English), both a string or a list of strings are OK.
        @return: dict of the structred attributes if the input is a string, list of dict if the input is a list.
        '''
        IF_INPUT_STR = type(args) is str
        if IF_INPUT_STR:
            args = [args]

        atts_extracted = []
        for prompt in tqdm(args):
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},    
                {"role": "user", "content": prompt}
            ]
            text = self.tokenizer.apply_chat_template(
                messages,    
                tokenize=False,    
                add_generation_prompt=True
            )
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

            generated_ids = self.model.generate(
                **model_inputs,    
                max_new_tokens=512
            )
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]

            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

            try:
                att_extracted = json.loads(response)
            except json.JSONDecodeError:
                logging.warning(
                    f"Cannot parse the results: {response} " +
                    f"From input prompt: {prompt}")
                atts_extracted.append({})
                continue

            atts_extracted.append(att_extracted)

        if IF_INPUT_STR:
            atts_extracted = atts_extracted[0]
        return atts_extracted

class PromptAttributeExtractor():
    def __init__(
            self,
            model_dir='checkpoints/Qwen-1_8B-Chat_finetune_20241207'):
        '''
        Init the class to extract structured attributes from the prompt(in English) using LLM.
        @param model_dir: the directory of the finetuned LLM model.
        @return: None
        '''
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_dir, # path to the output directory
            device_map="auto",
            trust_remote_code=True
        ).eval()

    def extract_attribute(
            self,
            args: Union[str, List[str]],
    ) -> Union[dict, List[dict]]:
        '''
        Extract structured attributes from the prompt(in English) using LLM.
        @param args: the input prompt(in English), both a string or a list of strings are OK.
        @return: dict of the structred attributes if the input is a string, list of dict if the input is a list.
        '''
        IF_INPUT_STR = type(args) is str
        if IF_INPUT_STR:
            args = [args]

        atts_extracted = []
        for prompt in tqdm(args):

            response, history = self.model.chat(self.tokenizer, prompt, history=None)
            try:
                att_extracted = json.loads(response)
            except json.JSONDecodeError:
                logging.warning(
                    f"Cannot parse the results: {response} " +
                    f"From input prompt: {prompt}")
                atts_extracted.append({})
                continue

            atts_extracted.append(att_extracted)

        if IF_INPUT_STR:
            atts_extracted = atts_extracted[0]
        return atts_extracted


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s: %(levelname)-7s[%(filename)s:%(lineno)-3s] %(message)s',
        datefmt='%d-%m-%Y:%H:%M:%S',
        level=getattr(logging, 'INFO'))

    args = _get_args()
    att_extractor = PromptAttributeExtractor(model_dir=args.checkpoint_path)

    prompt = "Blue eyes, upturned nose, long blonde hair, wearing a skirt, fashion, beautiful!"
    atts_extracted = att_extractor.extract_attribute(prompt)
    logging.info(f"\nPrompt: {prompt}\nAttribute: {atts_extracted}\n")

    prompt_list = [
        "a person looks like Jack Ma",
        "a handsome person",
        "good good study, day day up",
        "A chef with a long beard",
        "a student, he has fat face",
        "man, sword eyebrows, short red hair",
        "Chinese girl, Bobo haircut with a straight bangs, around 20 years old.",
        "Sharp-edged Japanese young man, with fluffy hair, monolid eyes, genteel demeanor wearing gold-rimmed glasses, and untamed eyebrows."
    ]
    atts_extracted_list = att_extractor.extract_attribute(prompt_list)
    for idx in range(len(prompt_list)):
        logging.info(f"\nPrompt: {prompt_list[idx]}\nAttribute: {atts_extracted_list[idx]}\n")