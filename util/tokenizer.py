#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
import glob
import os
import re
import json
import sys
import codecs
from es_interface import ESInterface
from nltk.tokenize.regexp import RegexpTokenizer
from util.extract_nlptags import Extract_NLP_Tags
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from copy import deepcopy
import shutil
from shutil import copyfile
from metamap14 import run as mm_run

tokenizer = RegexpTokenizer('[^\w\-\']+', gaps=True)
reserved_chars = ['+', '-', '&&', '||', '!', '(', ')',
                  '{', '}', '[', ']', '^', '"', '~',
                  '*', '?', ':', '\\', '/']

CMD = 'curl -XPOST \'http://localhost:9200/index_name/type/idx\' -d '

ref_topics = ["d1408_train_lewis",
              "d1419_train_yeoh",
              "d1415_train_blasco",
              "d1401_train_voorhoeve",
              "d1417_train_bos",
              "d1409_train_sherr",
              "d1414_train_vandelft",
              "d1412_train_cho",
              "d1403_train_serrano",
              "d1404_train_agamibernards",
              "d1413_train_figueroa",
              "d1402_train_westbrook",
              "d1411_train_fazi",
              "d1416_train_zhaowang",
              "d1407_train_toji",
              "d1406_train_hanahan",
              "d1405_train_campbell",
              "d1418_train_ying",
              "d1420_train_kumar",
              "d1410_train_wangtang", "doc"]


nlp_extractor = Extract_NLP_Tags()

def assign_str(text, idx, new_characters):
    '''
    Assigns the new_character to position idx of the str text
    '''
    return text[:idx] + new_characters + text[idx + len(new_characters):]


def filter(data):
    '''
    Filters the irrelevant part of the data

    Args: data(str)

    Returns: str
    '''
    forbidden = []
    match = re.search(r'\sopen archive\nabstract\n', data.lower())
    print len(data)
    if match is not None:
        data = assign_str(data, match.end() - 2, '. ')
    match = re.search(r'\ngo to:\nsummary\n', data.lower())
    if match is not None:
        data = assign_str(data, match.end() - 2, '. ')
    match = re.search(r'\s\sopen archive\n', data.lower())
    if match is not None:
        data = assign_str(data, match.end() - 2, '. ')
    match = re.search(r'\nabstract\n', data.lower())
    if match is not None:
        data = assign_str(data, match.end() - 2, '. ')
    match = re.search(r'\ngo to:\nsummary\n', data.lower())
    if match is not None:
        data = assign_str(data, match.end() - 2, '. ')

    return data

def _regex_end(regex, text):
    match = re.search(regex, text)
    return match.end() if match is not None else -1

def filter_text(sentences, offsets, data):
    forbidden = []
    new_sentences = []
    new_offsets = []
    beg = 0
    end = sys.maxint
    # summary_regex = r'\sopen archive\nabstract\n|' +\
    #     r'\s\sopen archive\n|' +\
    #     r'\ngo to:\nsummary\n|' +\
    #     r'\ngo to:\nabstract\n|' +\
    #     r'\sopen archive\nabstract\n|' +\
    #     r'\nabstract\n'
    # summary = -1
    # match = re.search(summary_regex, data.lower())
    # if match is not None:
    #     summary = match.end()
    summary = -1
    end = _regex_end('\sopen archive\nsummary\n', data.lower())
    if summary < end:
        summary = end
    end = _regex_end('\sopen archive\nabstract\n', data.lower())
    if summary < end:
        summary = end
    end = _regex_end('\s\s\sopen archive\n', data.lower())
    if summary < end:
        summary = end
    end = _regex_end('\ngo to:\nsummary\n', data.lower())
    if summary < end:
        summary = end
    end = _regex_end('\ngo to:\nabstract\n', data.lower())
    if summary < end:
        summary = end
    end = _regex_end('\nabstract\n', data.lower())
    if summary < end:
        summary = end

    table_regex = r'((\bTable\b \d+\n){2})(.*?)\n|((\bFigure\b \d+\n){2})(.*?)\n'
    table_regex2 = r'((\bTable\b \d+\r\n){2})(.*?)\r\n|((\bFigure\b \d+\r\n){2})(.*?)\r\n'
    table_regex3 = r'((\bTable\b \d+\. \n)((.|\n)*?)(\n\bTable options\b))|((\bTable\b \d+\. \r\n)((.|\r\n)*?)(\r\n\bTable options\b))'
    table_regex4 = r'\nTable\s\d\.\n(.*?)\nTable options\n'
    if summary > -1:
        beg = summary
    if beg > 0:
        forbidden.append((0, beg))
#     if (re.search(r'(\bFigure\b \d+\. \n)((.|\n)*?)(\n\bFigure options\b)', data)):
#         for m in re.finditer(r'(\bFigure\b \d+\. \n)((.|\n)*?)(\n\bFigure options\b)',
#                              data):
#             forbidden.append((m.start(), m.end()))

    if (re.search(table_regex, data)):
        for m in re.finditer(table_regex, data):
            forbidden.append((m.start(), m.end()))
#     elif (re.search(r'(\bFigure\b \d+\. \r\n)((.|\r\n)*?)(\r\n\bFigure options\b)', data)):
#         for m in re.finditer(r'(\bFigure\b \d+\. \r\n)((.|\r\n)*?)(\r\n\bFigure options\b)', data):
#             forbidden.append((m.start(), m.end()))
    if (re.search(table_regex2, data)):
        for m in re.finditer(table_regex2, data):
            forbidden.append((m.start(), m.end()))
    if (re.search(table_regex3, data)):
        for m in re.finditer(table_regex3, data):
            forbidden.append((m.start(), m.end()))
    if (re.search(table_regex4, data, re.DOTALL)):
        for m in re.finditer(table_regex4, data, re.DOTALL):
            forbidden.append((m.start(), m.end()))
    if data.lower().rfind('\nreferences') > -1:
        end = data.lower().rfind('\nreferences')
    if end < sys.maxint:
        forbidden.append((end, sys.maxint))
    pat = re.search(r'\bGo to:\nReferences\b\n', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))
    pat = re.search(r'\bGo to:\nAcknowledgements\n\b', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))
    pat = re.search(r'\bGo to:\nSupporting Information\b\n', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))
    pat = re.search(r'\bGo to:\nSupplementary Material\b\n', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))
    pat = re.search(r'\bAcknowledgments\n\b', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))
    pat = re.search(r'\bSupplemental Information\n\b', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))
    pat = re.search(r'\bGo to:\nFunding Statement\b', data)
    if pat and pat.start() < end:
        end = pat.start()
        forbidden.append((pat.start(), sys.maxint))

    print forbidden

    for idx, val in enumerate(sentences):
        okay = True
        noff = False
        nsent = False
        if offsets[idx][1] < offsets[idx][0]:
            okay = False
        if okay:
            for f_off in forbidden:
                if offsets[idx][0] >= f_off[0] and offsets[idx][1] <= f_off[1]:
                    okay = False
                elif offsets[idx][0] >= f_off[0] and offsets[idx][1] > f_off[1] and offsets[idx][0] < f_off[1]:
                    okay = False
                    noff = (f_off[1], offsets[idx][1])
                    nsent = data[f_off[1]:offsets[idx][1]]

#         if okay:
#             if re.search(r'\bfigure options\b', val, re.IGNORECASE) or\
#                     re.search(r'\bfull-size image\b \(\d+\ [KM]\)',
#                               val, re.IGNORECASE):
#                 okay = False
        if okay:
            new_sentences.append(val)
            new_offsets.append(offsets[idx])
        elif noff:
            new_sentences.append(nsent)
            new_offsets.append(noff)
    return {'sentences': new_sentences, 'offsets': new_offsets}


def direct_insert(res, out_file, index_name):
    """
    Directly inserts the records into elasticsearch
    """
    es_int = ESInterface(index_name=index_name)

    for k, v in res.iteritems():
        id = 0
        idx_type = k.lower().replace(',', '').replace('\'', '')
        for idx, val in enumerate(v['sentences']):
            val = re.sub('\[\d+\]', ' ', val)
            regex_citation = re.compile(r"\(\s?(([A-Za-z\-]+\s)+([A-Za-z\-]+\.?)?,?\s\d{2,4}(;\s)?)+\s?\)|"
                                        r"(\[(\d+([,–]\s?)?)+\])|"
                                        r"\[[\d,-]+\]|"
                                        r"\([fF]igures? \d+[A-Za-z]?.+?\)|"
                                        r"\(\s?[fF]igures? [A-Za-z]?\d+[A-Za-z]?.+?\)|"
                                        r"\(\s?[fF]igures? [A-Za-z]?\d+[A-Za-z]?\)").sub
            val = regex_citation('', val)
            val = re.sub('(' + '|'.join(re.escape(el) for el in
                                        reserved_chars) + ')',
                         r'\\\\\1',
                         val).replace('\'', '\u0027')\
                .replace('\r', '').replace('\n', '\\n')\
                .replace('\\\\"', '').replace('\t', '\\t')

            entry = "{\"sentence\":" + "\"" + val.\
                strip().encode('ascii', 'ignore') + "\","\
                + "\"offset\":\"" + str(v['offsets'][idx]) + "\"}"
            id += 1
            print entry
            es_int.add(index_name, idx_type, entry, docid=str(id).zfill(6))


def dump_for_index(res, out_file, index_name):
    #     es_int = ESInterface(index_name=index_name)
    cmd = CMD.replace('index_name', index_name)
    f = codecs.open(out_file, 'w', 'UTF-8')
    for k, v in res.iteritems():
        idx_type = k.lower().replace(',', '').replace('\'', '')
        for idx, val in enumerate(v['sentences']):
            val = re.sub('\[\d+\]', ' ', val)
            if 'figure' in val.lower():
                c = 1
            regex_citation = re.compile(r"\(\s?(([A-Za-z\-]+\s)+([A-Za-z\-]+\.?)?,?\s\d{2,4}(;\s)?)+\s?\)|"
                                        r"(\[(\d+([,–]\s?)?)+\])|"
                                        r"\[[\d,-]+\]|"
                                        r"\([fF]igures? \d+[A-Za-z]?.+?\)|"
                                        r"\(\s?[fF]igures? [A-Za-z]?\d+[A-Za-z]?.+?\)|"
                                        r"\(\s?[fF]igures? [A-Za-z]?\d+[A-Za-z]?\)").sub
            val = regex_citation('', val)
            val = re.sub('(' + '|'.join(re.escape(el) for el in
                                        reserved_chars) + ')',
                         r'\\\\\1',
                         val).replace('\'', '\u0027')\
                .replace('\r', '').replace('\n', '\\n')\
                .replace('\\\\"', '').replace('\t', '\\t')
            entry = "{\"sentence\":" + "\"" + val.\
                strip() + "\","\
                + "\"offset\":\"" + str(v['offsets'][idx]) + "\"}"
#             entry = filter(lambda x: x in string.printable, entry)
            print entry
#             try:
#                 es_int.add(index_name, idx_type, entry, str(idx).zfill(5))
#             except elasticsearch.exceptions.ConflictError:
#                 pass
            f.write(cmd.replace('idx', str(idx).zfill(5))
                    .replace('type', idx_type) +
                    '\'' + entry.lower() + '\'' + '\n')
    f.close()


def sent_tokenize(data):
    punkt_param = PunktParameters()
    punkt_param.abbrev_types = set(
        ['dr', 'vs', 'mr', 'mrs', 'prof', 'inc', 'et', 'al', 'Fig', 'fig'])
    sent_detector = PunktSentenceTokenizer(punkt_param)
    sentences = sent_detector.tokenize(data)
    offsets = sent_detector.span_tokenize(data)
    new_sentences = deepcopy(sentences)
    new_offsets = deepcopy(offsets)
    for i, off in enumerate(offsets):
        if len(tokenizer.tokenize(sentences[i])) < 7:  # Skip short sentences
            pass
        else:
            if i < len(offsets) - 1:
                if ((offsets[i + 1][0] - offsets[i][1]) < 5):
                    new_sentences.append(sentences[i] + ' ' + sentences[i + 1])
                    new_offsets.append((offsets[i][0], offsets[i + 1][1]))
            if i < len(offsets) - 2:
                if ((offsets[i + 2][0] - offsets[i + 1][1]) < 5) and\
                        ((offsets[i + 1][0] - offsets[i][0]) < 5):
                    new_sentences.append(
                        sentences[i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2])
                    new_offsets.append((offsets[i][0], offsets[i + 2][1]))
    #         if i < len(offsets) - 3:
    #             if (((offsets[i + 3][0] - offsets[i + 2][1]) < 5) and
    #                     ((offsets[i + 2][0] - offsets[i + 1][0]) < 5) and
    #                     ((offsets[i + 1][0] - offsets[i][0]) < 5)):
    #                 new_sentences.append(sentences[
    #                                   i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2] + ' ' + sentences[i + 3])
    #                 new_offsets.append((offsets[i][0], offsets[i + 3][1]))
    #         if i < len(offsets) - 4:
    #             if (((offsets[i + 4][0] - offsets[i + 3][1]) < 5) and
    #                  ((offsets[i + 3][0] - offsets[i + 2][1]) < 5) and
    #                     ((offsets[i + 2][0] - offsets[i + 1][0]) < 5) and
    #                     ((offsets[i + 1][0] - offsets[i][0]) < 5)):
    # if i < len(offsets) - 3:
    #             if (((offsets[i + 3][0] - offsets[i + 2][1]) < 5) and
    #                     ((offsets[i + 2][0] - offsets[i + 1][0]) < 5) and
    #                     ((offsets[i + 1][0] - offsets[i][0]) < 5)):
    #                 new_sentences.append(sentences[
    #                                   i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2] + ' ' + sentences[i + 3])
    #                 new_offsets.append((offsets[i][0], offsets[i + 3][1]))
    #         if i < len(offsets) - 4:
    #             if (((offsets[i + 4][0] - offsets[i + 3][1]) < 5) and
    #                  ((offsets[i + 3][0] - offsets[i + 2][1]) < 5) and
    #                     ((offsets[i + 2][0] - offsets[i + 1][0]) < 5) and
    #                     ((offsets[i + 1][0] - offsets[i][0]) < 5)):
    #                 new_sentences.append(sentences[
    #                                   i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2] + ' ' + sentences[i + 3] + ' ' + sentences[i + 3])
    #                 new_offsets.append((offsets[i][0], offsets[i + 3][1]))
    #         if i < len(offsets) - 5:
    #             if (((offsets[i + 5][0] - offsets[i + 4][1]) < 5) and
    #                 ((offsets[i + 4][0] - offsets[i + 3][1]) < 5) and
    #                  ((offsets[i + 3][0] - offsets[i + 2][1]) < 5) and
    #                     ((offsets[i + 2][0] - offsets[i + 1][0]) < 5) and
    #                     ((offsets[i + 1][0] - offsets[i][0]) < 5)):
    #                 new_sentences.append(sentences[
    #                                   i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2] + ' ' + sentences[i + 3] + ' ' + sentences[i + 3])
    #                 new_offsets.append((offsets[i][0], offsets[i + 3][1]))      new_sentences.append(sentences[
    #                                   i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2] + ' ' + sentences[i + 3] + ' ' + sentences[i + 3])
    #                 new_offsets.append((offsets[i][0], offsets[i + 3][1]))
    #         if i < len(offsets) - 5:
    #             if (((offsets[i + 5][0] - offsets[i + 4][1]) < 5) and
    #                 ((offsets[i + 4][0] - offsets[i + 3][1]) < 5) and
    #                  ((offsets[i + 3][0] - offsets[i + 2][1]) < 5) and
    #                     ((offsets[i + 2][0] - offsets[i + 1][0]) < 5) and
    #                     ((offsets[i + 1][0] - offsets[i][0]) < 5)):
    #                 new_sentences.append(sentences[
    #                                   i] + ' ' + sentences[i + 1] + ' ' + sentences[i + 2] + ' ' + sentences[i + 3] + ' ' + sentences[i + 3])
    #                 new_offsets.append((offsets[i][0], offsets[i + 3][1]))
    print new_offsets
    return {'sentences': new_sentences, 'offsets': new_offsets}


def merge(sentences, offsets, data):
    i = 0
    new_sentences = []
    new_offsets = []
    while i < (len(sentences)):
        new_sentence = sentences[i]
        begin = offsets[i][0]
        end = offsets[i][1]
        while len(sentences[i]) < 20 and i < len(sentences) - 1:
            new_sentence = sentences[i] + ' ' + sentences[i + 1]
            end = offsets[i + 1][1]
            i += 1
        new_sentences.append(new_sentence)
        new_offsets.append((begin, end))
        i += 1
    return {'sentences': new_sentences, 'offsets': new_offsets}


def para_tokenize(data):
    nummatch = 0
    regexp = r'(?s)((?:[^\n][\n]?)+)'
    sentences = []
    offsets = []
    for m in re.finditer(regexp, data):
        nummatch += 1
    if nummatch < 2:
        regexp = r'(?s)((?:[^\r\n][\r\n]?)+)'
    for m in re.finditer(regexp, data):
        sentences.append(m.group(0))
        offsets.append((m.start(), m.end()))
    return {'sentences': sentences, 'offsets': offsets}


def tokenize(opts, args):
    if opts.input_type == 'dir':
        out = {}
        topic_name = ''
        for path in glob.glob(opts.input_path + '/*/Documents_Text/*.txt'):
            parent_dir = os.path.abspath(os.path.join(path, os.pardir))
            topic_dir = os.path.abspath(os.path.join(parent_dir, os.pardir))
            if topic_name != topic_dir[topic_dir.rfind('/') + 1:]:
                topic_name = topic_dir[topic_dir.rfind('/') + 1:]
                print 'processing topic:' + topic_name
            idx_type = topic_name + '_' + \
                path[
                    path.rfind('/') + 1:path.rfind('.')].\
                replace(',', '').replace('\'', '')
            if idx_type.lower() not in ref_topics:
                print "[Info] Skipping topic: %s, not a reference topic" % idx_type
            else:
                copyfile(path, '/home/ac1450/dev/git/biosum/tmp/data/' + idx_type)
                try:
                    with codecs.open(path, "rb", 'UTF-8') as myfile:
                        data = myfile.read().replace('\r', '')
                except:
                    with codecs.open(path, "rb", 'ISO-8859-1') as myfile:
                        data = myfile.read().replace('\r', '')
                if opts.mode == 'sent':
                    res = sent_tokenize(filter(data))
                    if opts.merge:
                        res = merge(res['sentences'], res['offsets'], data)
                if opts.mode == 'para':
                    res = para_tokenize(data)
                if opts.filter:
                    res = filter_text(res['sentences'], res['offsets'], data)
                out[idx_type] = {'sentences': res['sentences'],
                                 'offsets': res['offsets']}
        for k, v in out.iteritems():
            out[k]['nlp'] = {'tags': nlp_extractor.extract_nlp(sent) for sent in v['sentences']}
            out[k]['mm'] = {'mm_concepts': mm_run(sent) for sent in v['sentences']}
        if opts.direct_index:
            direct_insert(out, opts.out_file, index_name=opts.direct_index)
            return out
        if not opts.is_index:
            try:
                with codecs.open(opts.out_file, "wb", 'UTF-8') as myfile:
                    json.dump(out, myfile, indent=2)
            except:
                with codecs.open(opts.out_file, "wb", 'ISO-8859-1') as myfile:
                    json.dump(out, myfile, indent=2)
        else:
            dump_for_index(out, opts.sh_file, opts.index_name)
        return out
    elif opts.input_type == 'text':
        try:
            with codecs.open(path, "rb", 'UTF-8') as myfile:
                data = myfile.read().replace('\r', '')
        except:
            with codecs.open(path, "rbU", 'ISO-8859-1') as myfile:
                data = myfile.read().replace('\r', '')
        res = sent_tokenize(filter(data))
        if opts.filter:
            res = filter_text(res['sentences'], res['offsets'], data)
        out = {'sentences': res['sentences'],
               'offsets': res['offsets']}
        if opts.direct_index:
            direct_insert(out, opts.out_file, index_name=opts.direct_index)
            return out
        if not opts.is_index:
            try:
                with codecs.open(path, "w", 'UTF-8') as myfile:
                    json.dump(out, opts.out_file, indent=2)
            except:
                with codecs.open(path, "rbU", 'ISO-8859-1') as myfile:
                    json.dump(out, opts.out_file, indent=2)
        else:
            dump_for_index(out, opts.sh_file, opts.index_name)
        return out


if __name__ == '__main__':
    ap = ArgumentParser(usage='example args: \n'
                        '<< -m sent -it dir -i TAC_2014_BiomedSumm'
                        '_Training_Data_V1.1/data -o out_file.json >>\n'
                        'tokenizes the TAC data to sentences \n\n'
                        '<< -m sent -it text -i input.txt -o'
                        ' out_file.json>> \nR'
                        'tokenizes input.txt to sentences \n\n'
                        '<< -m para -it dir -i TAC_2014_BiomedSumm'
                        '_Training_Data_V1.1/data -o out_file.json >> \n'
                        'tokenizes the TAC data to paragraphs'
                        )
    ap.add_argument('-m', '--mode', dest="mode",
                    default='sent', help='mode can be sent (for sentence tokenization)\
                     or para (for paragraph tokenization), default=sent')
    ap.add_argument('-it', '--input-type', dest='input_type',
                    default='dir', help='input-type can be the data'
                    ' folder of the tac-dataset,'
                    'or can be an arbitrary text file. Valid options: dir, text ')
    ap.add_argument('-f', '--filter', dest='filter',
                    action='store_false', help='filter non relevant parts'
                    ' (e.g figures, tables, references, etc)')
    ap.add_argument('-i', '--input-path', dest='input_path',
                    help='input path to the data dir of TAC dataset or a'
                    ' simple text file (for text input type)')
    ap.add_argument('-o', '--out-file', dest='out_file',
                    help='destination for dumping the output')
    ap.add_argument('-sh', '--sh-file', dest='sh_file',
                    help='destination for dumping the output')
    ap.add_argument('-mrg', '--merge', dest='merge', action='store_false',
                    help='merge short tokens to form a longer one'
                    ' (only available in sent_tokenizer)')
    ap.add_argument('-idx', '--index-name', dest='index_name',
                    help='name of the index')
    ap.add_argument('--is-index', dest='is_index', action='store_true',
                    help='output file is in a format to be ready to be run'
                    ' to be indexed')
    ap.add_argument('--direct-index', dest='direct_index',
                    help='directly inserts into elasticsearch')

    opts, args = ap.parse_known_args()
    tokenize(opts, args)
