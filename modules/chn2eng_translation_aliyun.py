
import json
import os
import re
import sys
from typing import List, Union

from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_console.client import Client as ConsoleClient
from alibabacloud_tea_util.client import Client as UtilClient
import logging

logger = logging.getLogger(__name__)


class Chn2EngTranslation(object):
    def __init__(
            self,
            error_mapping_pre_filepath='assets/configs/translation/mapping_list_pre.json',
            error_mapping_post_filepath='assets/configs/translation/mapping_list_post.json',
            access_key_id=None, access_key_secret=None,
            # access_key_filepath='assets/configs/translation/aliyun_access_key.json'
            ):
        """
        Init the class which translate chinese to english.
        @param error_mapping_pre_filepath: the json file storing pre-translation informations.
        @param error_mapping_post_filepath: the json file storing error correction informations during post-processing.
        @param access_key_id: aliyun access key id for translation.
        @param access_key_secret: aliyun access key secret for translation.
        @param access_key_filepath: config file which stores aliyun access key for translation.
        @return: None
        """
        # 先使用函数参数，如没有则使用环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET，否则使用配置文件。
        # 配置文件泄露可能会导致 AccessKey 泄露，并威胁账号下所有资源的安全性。
        # 更多鉴权访问方式请参见：https://help.aliyun.com/document_detail/378659.html
        ALIBABA_CLOUD_ACCESS_KEY_ID = os.getenv('Translate_AK')
        ALIBABA_CLOUD_ACCESS_KEY_SECRET = os.getenv('Translate_SK')
        if access_key_id is not None and access_key_secret is not None:
            self.ALIBABA_CLOUD_ACCESS_KEY_ID = access_key_id
            self.ALIBABA_CLOUD_ACCESS_KEY_SECRET = access_key_secret
        elif ALIBABA_CLOUD_ACCESS_KEY_ID is not None and ALIBABA_CLOUD_ACCESS_KEY_SECRET is not None:
            self.ALIBABA_CLOUD_ACCESS_KEY_ID = ALIBABA_CLOUD_ACCESS_KEY_ID
            self.ALIBABA_CLOUD_ACCESS_KEY_SECRET = ALIBABA_CLOUD_ACCESS_KEY_SECRET
        else:
            logger.info(f'NO ALIBABA_CLOUD_ACCESS_KEY_ID&ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        
        self.mapping_list_pre = []
        try:
            with open(error_mapping_pre_filepath, 'r') as f:
                self.mapping_list_pre = json.load(f)
        except:
            print(f'Error during read mapping file {error_mapping_pre_filepath}')

        self.mapping_list_post = []
        try:
            with open(error_mapping_post_filepath, 'r') as f:
                self.mapping_list_post = json.load(f)
        except:
            print(f'Error during read mapping file {error_mapping_post_filepath}')

    @staticmethod
    def create_client(
        access_key_id: str,
        access_key_secret: str,
    ) -> alimt20181012Client:
        """
        使用AK&SK初始化账号Client
        @param access_key_id:
        @param access_key_secret:
        @return: Client
        @throws Exception
        """
        config = open_api_models.Config(
            # 必填，您的 AccessKey ID,
            access_key_id=access_key_id,
            # 必填，您的 AccessKey Secret,
            access_key_secret=access_key_secret
        )
        # Endpoint 请参考 https://api.aliyun.com/product/alimt
        config.endpoint = f'mt.aliyuncs.com'
        return alimt20181012Client(config)

    @staticmethod
    def create_client_with_sts(
        access_key_id: str,
        access_key_secret: str,
        security_token: str,
    ) -> alimt20181012Client:
        """
        使用STS鉴权方式初始化账号Client，推荐此方式。
        @param access_key_id:
        @param access_key_secret:
        @param security_token:
        @return: Client
        @throws Exception
        """
        config = open_api_models.Config(
            # 必填，您的 AccessKey ID,
            access_key_id=access_key_id,
            # 必填，您的 AccessKey Secret,
            access_key_secret=access_key_secret,
            # 必填，您的 Security Token,
            security_token=security_token,
            # 必填，表明使用 STS 方式,
            type='sts'
        )
        # Endpoint 请参考 https://api.aliyun.com/product/alimt
        config.endpoint = f'mt.aliyuncs.com'
        return alimt20181012Client(config)

    def translate_eng(
        self,
        args: Union[str, List[str]],
    ) -> Union[str, List[str]]:
        client = Chn2EngTranslation.create_client(
            self.ALIBABA_CLOUD_ACCESS_KEY_ID,
            self.ALIBABA_CLOUD_ACCESS_KEY_SECRET)
        IF_INPUT_STR = type(args) is str
        if IF_INPUT_STR:
            args = [args]
        translated_results = []
        for src_text in args:
            # Pre-process: pre-translate some phraces into english.
            for mapping_desc in self.mapping_list_pre:
                src = mapping_desc['src']
                dst = mapping_desc['dst']
                src_text = re.sub(src, dst, src_text)
            
            # Translate using ALIMT.
            translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
                    format_type = 'text',
                    scene = 'general',
                    source_language = 'zh',
                    source_text = src_text,
                    target_language = 'en'
                )
            runtime = util_models.RuntimeOptions()
            resp = client.translate_general_with_options(translate_general_request, runtime)
            # ConsoleClient.log(UtilClient.to_jsonstring(resp))
            translated_str = resp.body.data.translated

            # Post-process: fix some un-resonable phases.
            for mapping_desc in self.mapping_list_post:
                src = mapping_desc['src']
                dst = mapping_desc['dst']
                translated_str = re.sub(src, dst, translated_str, flags=re.IGNORECASE)
            
            translated_results.append(translated_str)

        if IF_INPUT_STR:
            translated_results = translated_results[0]
        return translated_results

    def translate_chn(
        self,
        args: Union[str, List[str]],
    ) -> Union[str, List[str]]:
        client = Chn2EngTranslation.create_client(
            self.ALIBABA_CLOUD_ACCESS_KEY_ID,
            self.ALIBABA_CLOUD_ACCESS_KEY_SECRET)
        IF_INPUT_STR = type(args) is str
        if IF_INPUT_STR:
            args = [args]
        translated_results = []
        for src_text in args:
            ## Pre-process: pre-translate some phraces into english.
            # for mapping_desc in self.mapping_list_pre:
            #     src = mapping_desc['src']
            #     dst = mapping_desc['dst']
            #     src_text = re.sub(src, dst, src_text)
            
            # Translate using ALIMT.
            translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
                    format_type = 'text',
                    scene = 'general',
                    source_language = 'auto',
                    source_text = src_text,
                    target_language = 'zh'
                )
            runtime = util_models.RuntimeOptions()
            resp = client.translate_general_with_options(translate_general_request, runtime)
            # ConsoleClient.log(UtilClient.to_jsonstring(resp))
            translated_str = resp.body.data.translated

            ## Post-process: fix some un-resonable phases.
            # for mapping_desc in self.mapping_list_post:
            #     src = mapping_desc['src']
            #     dst = mapping_desc['dst']
            #     translated_str = re.sub(src, dst, translated_str, flags=re.IGNORECASE)
            
            translated_results.append(translated_str)

        if IF_INPUT_STR:
            translated_results = translated_results[0]
        return translated_results


if __name__ == '__main__':
    chinese_prompt = "一个圆脸，丹凤眼的中国女孩，蓝色眼睛，柳叶眉"
    translator = Chn2EngTranslation()
    english_prompt = translator.translate(chinese_prompt)
    logger.info(english_prompt)
