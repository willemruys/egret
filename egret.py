# egret.py: Command line interface for EGRET
#
# Copyright (C) 2016-2018  Eric Larson and Anna Kirk
# elarson@seattleu.edu
#
# This file is part of EGRET.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import re
import sys
from xml.etree.ElementInclude import include
import egret_ext
from optparse import OptionParser
#import time

# Precondition: regexStr successfully compiles and all strings in testStrings
# match the regular expression


def get_group_info(regexStr, testStrings, namedOnly):
    # check for empty list
    if len(testStrings) == 0:
        return {}

    # compile regex
    regex = re.compile(regexStr)

    # determine if there are named groups, numbered groups, or no groups
    match = regex.fullmatch(testStrings[0])
    if len(match.groupdict()) != 0:
        useNames = True
        names = list(match.groupdict().keys())
        nameList = []
        for name in names:
            r = r"\?P<" + name
            start = re.search(r, regexStr).start()
            nameList.append((start, name))
        nameList = sorted(nameList)
        groupHdr = [name for (start, name) in nameList]
    elif len(match.groups()) != 0:
        if namedOnly:
            return None
        useNames = False
    else:
        return None

    # get groups for each string
    groupDict = {}
    for testStr in testStrings:
        match = regex.fullmatch(testStr)
        if useNames:
            g = match.groupdict()
            groupList = []
            for i in groupHdr:
                groupList.append({i: g[i]})
            groupDict[testStr] = groupList
        else:
            groupDict[testStr] = match.groups()

    return groupDict


parser = OptionParser()
parser.add_option("-f", "--file", dest="fileName",
                  help="file containing regex")
parser.add_option("-r", "--regex", dest="regex", help="regular expression")
parser.add_option("-b", "--base_substring", dest="baseSubstring",
                  default="evil", help="base substring for regex strings")
parser.add_option("-o", "--output_file", dest="outputFile",
                  help="output file name")
parser.add_option("-d", "--debug", action="store_true", dest="debugMode",
                  default=False, help="display debug info")
parser.add_option("-s", "--stat", action="store_true", dest="statMode",
                  default=False, help="display stats")
parser.add_option("-g", "--groups", action="store_true", dest="showGroups",
                  default=False, help="show groups")
parser.add_option("-n", "--named_groups", action="store_true", dest="showNamedGroups",
                  default=False, help="only show named groups")
opts, args = parser.parse_args()

# check for valid command lines
if opts.fileName != None and opts.regex != None:
    print("Cannot specify both a regular expression and input file")
    sys.exit(-1)

# get the regular expression
output = []
descStr = []
regexStrings = []
if opts.fileName != None:
    inFile = open(opts.fileName)

    fileAsJson = json.load(inFile)
    for regexObject in fileAsJson:
        regexStrings.append(regexObject['pattern'])
        try:
            descStr.append(regexObject['pattern'])
        except:
            continue
        inFile.close()

regexStrings.remove('[A-Za-zÀ-ÖØ-öø-ÿ]\\S*')
regexStrings.remove('[eÃ©]$')
regexStrings.remove('([アァカヵガサザタダナハバパマヤャラワヮヷ])ー')
regexStrings.remove('^[Â£$â‚¬?.]')
regexStrings.remove('^[a-zA-Z0-9?!§$%#]$')
regexStrings.remove('[ťţŧț]')
regexStrings.remove('□[^▽]')
regexStrings.remove('^[0-9 ]+丁目[0-9 ]+番?')
regexStrings.remove('[\x00-\x08,\x0b-\x0c,\x0e-x1F,\x7f]')
regexStrings.remove('((\s*<[NS]>\s*,\s*){100,})')
regexStrings.remove('^([А-ЯЁ]{1})([а-яё]{1,15})$')
regexStrings.remove(
    "^(?:(?:(?:https?|ftp):)?\\/\\/)(?:\\S+(?::\\S*)?@)?(?:(?!(?:10|127)(?:\\.\\d{1,3}){3})(?!(?:169\\.254|192\\.168)(?:\\.\\d{1,3}){2})(?!172\\.(?:1[6-9]|2\\d|3[0-1])(?:\\.\\d{1,3}){2})(?:[1-9]\\d?|1\\d\\d|2[01]\\d|22[0-3])(?:\\.(?:1?\\d{1,2}|2[0-4]\\d|25[0-5])){2}(?:\\.(?:[1-9]\\d?|1\\d\\d|2[0-4]\\d|25[0-4]))|(?:(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)(?:\\.(?:[a-z\\u00a1-\\uffff0-9]-*)*[a-z\\u00a1-\\uffff0-9]+)*(?:\\.(?:[a-z\\u00a1-\\uffff]{2,})).?)(?::\\d{2,5})?(?:[/?#]\\S*)?$")

# compile the regular expression
for regexStr in regexStrings:
    compileRegex = True
    exception = ''
    hasError = False
    # capture regex patterns containing special characters
    # if 'â' not in regexStr or 'Â' or regexStr or '¬' not in regexStr and '([アァカヵガサザタダナハバパマヤャラワヮヷ])ー' not in regexStr:
    try:
        regex = re.compile(regexStr)
        inputStrs = [10]
        # execute regex-test
        #start_time = time.process_time()
        inputStrs = egret_ext.run(regexStr, opts.baseSubstring,
                                  False, False, False, False)
        status = inputStrs[0]
        hasError = (status[0:5] == "ERROR")
        # in this case, an error is thrown by EGRET
        if status and status[0:5] == "ERROR":
            output.append({'regex': regexStr, 'exceptionStackTrace': {
                'exceptionThrownBy': 'EGRET',
                'exception': status
            },
                'matches': []})
            hasError = True
            continue

    # here we catch errors thrown by the re library
    except re.error as e:
        # if e.msg.find('escape') != -1 or e.msg.find('unterminated subpattern') != -1 or e.msg.find('unsupported character') != -1 or e.msg.find('unknown extension') != -1:
        #     exception = e.msg
        #     hasError = True
        #     output.append({'regex': regexStr, 'exception': exception,
        #                   'matches': [], 'exceptionThrownBy': 'Python'})
        #     continue
        output.append({'regex': regexStr, 'exceptionStackTrace': {
            'exceptionThrownBy': 'Python',
            'exception':  e.msg
        },
            'matches': [], })
        hasError = True
        continue

    if hasError:
        alerts = [status]
    else:
        idx = 0
        line = inputStrs[idx]
        while line != "BEGIN":
            idx += 1
            line = inputStrs[idx]
        if idx == 0:
            alerts = []
            inputStrs = inputStrs[1:]
        else:
            alerts = inputStrs[:idx]
            inputStrs = inputStrs[idx+1:]
    output.append(
        {'regex': regexStr, 'exceptionStackTrace': None, 'matches': inputStrs})

# open output file
if opts.outputFile:
    outFile = open(opts.outputFile, 'w')
    if hasError:
        outFile.close()
        sys.exit(-1)
else:
    print()
    print(header, end='')
    if hasError:
        sys.exit(-1)

# dump output to output file
json.dump(output, outFile)

if opts.outputFile:
    outFile.close()

sys.exit(0)
