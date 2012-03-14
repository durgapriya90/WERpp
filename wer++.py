#!/usr/bin/env python
# -*- coding: utf-8 -*-

# werpp.py: Calculates WER and paints the edition operations
# Copyright (C) 2011 Nicolás Serrano Martínez-Santos <nserrano@dsic.upv.es>
# Contributors: Guillem Gasco
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import codecs
import re
from random import shuffle
from sys import argv,stderr,stdout
from optparse import OptionParser
import codecs

class FileReader:
  def __init__(self,f,buffer_size=1024):
    #open file
    self.f = f
    self.buffer_size = 1024
    self.buff_readed = 0
    self.buff_len = 0

  def read_buff(self):
    self.buff = self.f.read(self.buffer_size)

    self.buff_len = len(self.buff)
    self.buff_readed = 0

    if self.buff_len == 0:
      return False
    else:
      return True

  def readline(self):
    s = ""
    while 1:
      while self.buff_readed < self.buff_len:
        if self.buff[self.buff_readed] == '\n':
          self.buff_readed+=1
          return s
        else:
          s+=self.buff[self.buff_readed]
          self.buff_readed+=1

      if not self.read_buff():
        return None

  def close(self):
    self.f.close()

#awk style dictionary
class D(dict):
  def __getitem__(self, i):
    if i not in self: self[i] = 0
    return dict.__getitem__(self, i)

class color:
  d={}; RESET_SEQ=""
  def __init__(self,c):
    if c == True:
      self.d['K']="\033[0;30m"    # black
      self.d['R']="\033[0;31m"    # red
      self.d['G']="\033[0;32m"    # green
      self.d['Y']="\033[0;33m"    # yellow
      self.d['B']="\033[0;34m"    # blue
      self.d['M']="\033[0;35m"    # magenta
      self.d['C']="\033[0;36m"    # cyan
      self.d['W']="\033[0;37m"    # white
      self.RESET_SEQ = "\033[0m"
    else:
      self.d['K']="["
      self.d['R']="["
      self.d['G']="["
      self.d['Y']="["
      self.d['B']="["
      self.d['M']="["
      self.d['C']="["
      self.d['W']="["
      self.RESET_SEQ = "]"

  def c_string(self,color,string):
    return self.d[color]+string+self.RESET_SEQ

# Normal compare strings
def string_equal(str1,str2):
  return (str1 == str2)

# Ignore simbol #
def dummy_string_equal(str1,str2):
  return (str1.replace("#","") == str2)

def string_equal_lowercase(str1,str2):
  return (str1.lower() == str2.lower())

#read lines and return its simbol representation
def char_to_num(x):
  res =""
  s=x
  for i in s:
    if i == " ":
      res += "__ "
    else:
      res += "%d " %ord(i)
  return res[:-1]

def num_to_char(j):
  if j != "__":
    return unichr(int(j))
  else:
    return j

def lev_changes(str1, str2, i_cost, d_cost, d_sub,vocab={}, eq_func=string_equal):
  d={}; sub={};
  for i in range(len(str1)+1):
    d[i]=dict()
    d[i][0]=i
    sub[i]={}
    sub[i][0]="D"
  for i in range(len(str2)+1):
    d[0][i] = i
    sub[0][i]="I"
  for i in range(1, len(str1)+1):
    for j in range(1, len(str2)+1):
      if d[i][j-1]+i_cost < d[i-1][j]+d_cost and d[i][j-1] < d[i-1][j-1]+(not eq_func(str1[i-1],str2[j-1]))*d_sub:
        if vocab=={} or (str2[j-1] in vocab):
          sub[i][j] = "I";
        else:
          sub[i][j] = "O"; #Oov insertion
      elif d[i-1][j]+d_cost < d[i][j-1]+i_cost and d[i-1][j] < d[i-1][j-1]+(not eq_func(str1[i-1],str2[j-1]))*d_sub:
        sub[i][j] = "D";
      else:
        if eq_func(str1[i-1],str2[j-1]):
          sub[i][j] = "E";
        else:
          if vocab=={} or (str2[j-1] in vocab):
            sub[i][j] = "S";
          else:
            sub[i][j] = "A"; #Oov Substitution
      d[i][j] = min(d[i][j-1]+i_cost, d[i-1][j]+d_cost, d[i-1][j-1]+(not eq_func(str1[i-1],str2[j-1]))*d_sub)

  i=len(str1); j=len(str2); path=[]
  while(i > 0 or j > 0):
    path.append([sub[i][j],i-1,j-1])
    if(sub[i][j] == "I" or sub[i][j] == "O"):
      j-=1
    elif(sub[i][j] == "D"):
      i-=1
    else:
      j-=1; i-=1;
  path.reverse()
  return path

def calculate_statistics(rec_file,ref_file,vocab,options):
  subs={}; subs_counts=D(); subs_all = 0
  ins=D(); ins_all = 0
  dels=D(); dels_all = 0

  join_symbol="@"
  colors=color(options.color)
  oovSubs=0
  oovIns=0
  oovs = 0
  ref_count=0

  eq_func = string_equal

  #change compare function
  if options.equal_func == "dummy":
    eq_func = dummy_string_equal
  elif options.equal_func == "lower":
    eq_func = string_equal_lowercase

  excps = []
  if options.excp_file != None:
    f = codecs.open(options.excp_file,"r","utf-8")
    for i in f.readlines():
      excps.append(i[:-1])
    f.close()

  if options.v == True:
    stdout.write(colors.RESET_SEQ)

  i = rec_file.readline()
  while len(i) != 0:
    j = ref_file.readline()

    #delete some symbols
    if options.excp_file != None:
      for e in excps:
        i = i.replace(e,"")
        j = j.replace(e,"")

    if options.cer:
      i = char_to_num(i[:-1])
      j = char_to_num(j[:-1])

    w_i = i.split()
    w_j = j.split()

    ref_count+= len(w_j)

    changes = lev_changes(w_i,w_j,1,1,1,vocab,eq_func)

    if options.v == True:
      stdout.write("[II] ")
    #verbose variables
    v_editions=0

    for i in changes:
      [edition, rec_p, ref_p] = i
      rec = w_i[rec_p] if len(w_i) > 0 else "#"
      ref = w_j[ref_p]
      if options.cer:
        rec = num_to_char(rec)
        ref = num_to_char(ref)

      #color the operations
      if options.v == True:
        str_out = ""
        if edition == 'S':
          str_out = "%s" %(colors.c_string("B",rec+join_symbol+ref).encode("utf-8"))
        elif edition == 'A':
          str_out = "%s" %(colors.c_string("Y",rec+join_symbol+ref).encode("utf-8"))
        elif edition == 'I':
          str_out = "%s" %(colors.c_string("G",ref).encode("utf-8"))
        elif edition == 'D':
          str_out = "%s" %(colors.c_string("R",rec).encode("utf-8"))
        elif edition == 'O':
          str_out = "%s" %(colors.c_string("Y",ref).encode("utf-8"))
        else:
          str_out = "%s" %ref.encode("utf-8")
        if not options.cer:
          str_out = str_out+" "
        elif "__" in str_out:
          str_out = " "+str_out+" "
        stdout.write(str_out)


      #count the segment where the errors occur
      if edition != 'E':
        #WER on each line
        if options.V == 1:
          v_editions+=1
        if options.vocab != None:
          if ref not in vocab:
            oovs+=1

      #count events in dictionaries
      if edition == 'S' or edition == 'A':
        subs_all+=1
        if edition == 'A':
          oovSubs+=1
        if options.n > 0:
          if ref not in subs:
            subs[ref]={}
          if rec not in subs[ref]:
            subs[ref][rec] = 1
          else:
            subs[ref][rec]+=1
        subs_counts[ref]+=1

      elif edition == 'I' or edition == 'O':
        if edition == 'O':
          oovIns+=1
        ins_all+=1
        ins[ref]+=1
      elif edition == 'D':
        dels_all+=1
        dels[rec]+=1

    if options.v == True:
      stdout.write("\n")

    if options.V == 1:
      stdout.write("[II] WER-per-sentence Eds: %d Ref: %d\n" %(v_editions,len(w_j)))

    i = rec_file.readline()

  stdout.write("WER: %.2f (Ins: %d Dels: %d Subs: %d Ref: %d )" \
      %(float(subs_all+ins_all+dels_all)/ref_count*100,ins_all,dels_all,subs_all,ref_count))

  if options.vocab != None:
   # stdout.write(" OOVs: %.2f%%" %(float(oovs)/ref_count*100))
    stdout.write(" OOVs: %.2f%%" %(float(oovSubs+oovIns)/ref_count*100))
    stdout.write(" OOVsSubs: %.2f%%" %(float(oovSubs)/subs_all*100))
    stdout.write(" OOVsIns: %.2f%%" %(float(oovIns)/ins_all*100))
  stdout.write("\n")

  if options.n > 0:
    stdout.write("----------------------------------\nWer due to words words\n----------------------------------\n")
    events=[]
    for i in subs:
      for j in subs[i]:
        events.append([subs[i][j],['S',i,j]])
    for i in ins:
      events.append([ins[i],['I',i]])
    for i in dels:
      events.append([dels[i],['D',i]])

    events.sort(); acc=0
    for i in range(len(events)-1,len(events)-1-options.n,-1):
      [n, e] = events[i]
      s=""
      if 'S' in e:
        s=colors.c_string("B",e[2]+join_symbol+e[1])
      elif 'I' in e:
        s=colors.c_string("G",e[1])
      elif 'D' in e:
        s=colors.c_string("R",e[1])
      acc+=n
      stdout.write("[Worst-%.2d] %.4f%% %.4f%% - %s\n" %(len(events)-1-i+1, float(n)/ref_count*100,float(acc)/ref_count*100, s.encode("utf-8")))

def main():
  cmd_parser = OptionParser(usage="usage: %prog [options] recognized_file reference_file")
  cmd_parser.add_option('-v',
      action="store_true",dest="v",
      help='Verbose power on!')
  cmd_parser.add_option('-V', '--verbose',
     action="store", type="int", dest="V", default=0, help='Verbose level')
  cmd_parser.add_option('-n', '--worst-events',
     action="store", type="int", dest="n", default=0, help='Words words to print')
  cmd_parser.add_option('-e', '--equal-func',
     action="store", type="string", dest="equal_func", default="standard", help='String compare function=[ '
     'standard , dummy, lower ]')
  cmd_parser.add_option('--cer',
     action="store_true", dest="cer", help='Calculate Character Error Rate')
  cmd_parser.add_option('-f', '--excp-file',
     action="store", type="string", dest="excp_file",  help='File containing the characters to delete')
  cmd_parser.add_option('-c', '--colors',
      action="store_true",dest="color",
      help='Color the output')
  cmd_parser.add_option('-O', '--vocab',
     action="store", type="string", dest="vocab", default=None, help='Vocabulary to count OOVs')

  cmd_parser.parse_args(argv)
  (opts, args)= cmd_parser.parse_args()

  vocab = {}
  if opts.vocab != None:
    f = codecs.open(opts.vocab,"r","utf-8")
    for i in f.readlines():
      for j in i.split():
        if j not in vocab:
          vocab[j]=1

  if len(args) != 2:
    cmd_parser.print_help()
    exit(1)

  rec_file = codecs.open(args[0],"r","utf-8")
  ref_file = codecs.open(args[1],"r","utf-8")
  rec_file_reader = FileReader(rec_file)
  ref_file_reader = FileReader(ref_file)

  calculate_statistics(rec_file,ref_file,vocab,opts)

if __name__ == "__main__":
  main()

