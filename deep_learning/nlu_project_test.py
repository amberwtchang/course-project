# -*- coding: utf-8 -*-
"""nlu_project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1lUDqwC1LJyYQpIg4MO0WEZQx43OVE3c0
"""

#!pip install seqeval[cpu]

# Upload data from Google Drive
#from google.colab import drive
#drive.mount('/content/drive')

#check files under this path
import os

#path = "/content/drive/My Drive/Colab Notebooks/nlu_task/"

#os.chdir(path)
#os.listdir(path)

import pandas as pd
import numpy as np
import json

df = pd.read_json('train_iob.json')
df

df_test_ori = pd.read_json('test.json')
df_test = df_test_ori.T 
df_test

#make fake label
fake_label = []
fake_iob = []
for sent in df_test["text"]:
  #print(sent)
  for tok in sent.split():
    #print(tok)
    fake_iob.append("O")
  #print(fake_iob)
  fake_label.append(fake_iob)
  fake_iob = []
#print(fake_label)
#print(fake_label[0])  

df_test["fake_label"] = fake_label
df_test

#train set
#get sentences
sentences = df["text"].tolist()
print(sentences[0])

#get max length
length = 0
for sent in sentences:
  if len(sent) > length:
    length = len(sent)
print("max_length of train: ", length)

#dev set
#get sentences
sentences_test = df_test["text"].tolist()
print(sentences_test[0])

#get max length
length = 0
for sent in sentences_test:
  if len(sent) > length:
    length = len(sent)
print("max_length of test: ", length)

#get labels
labels = df["IOB_complete"].tolist()
#labels[0]

#check this again
tags = []
for lab in labels:
  for l in lab:
    tags.append(l)
#print("This is tags: ", tags)

tags_vals = list(set(tags))
tag2idx = {t: i for i, t in enumerate(tags_vals)}
print("This is tags_vals: ", tags_vals)
print("This is tag2idx: ", tag2idx)
#print(tag2idx["O"])

#get fake labels
labels_test = df_test["fake_label"].tolist()
#labels_test[0]

#check this again
tags_test = []
for lab in labels_test:
  for l in lab:
    tags_test.append(l)
#print(tags_test)

#!pip install transformers
#!pip3 install torch torchvision
from transformers import BertTokenizer, BertForTokenClassification
from tqdm import tqdm, trange

#!pip install pytorch-pretrained-bert
import torch
from torch.optim import Adam
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from pytorch_pretrained_bert import BertTokenizer, BertConfig
from pytorch_pretrained_bert import BertForTokenClassification, BertAdam

MAX_LEN = 186
batch_size = 64

#device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#n_gpu = torch.cuda.device_count()

#torch.cuda.get_device_name(0)

"""# For sentences tokenization & encoding"""

#import tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)

#tokenize train set
tokenized_texts = [tokenizer.tokenize(sent) for sent in sentences]
print("tokenized_texts[0]: ")
print(tokenized_texts[0])
print()

#encode train set
input_ids = pad_sequences([tokenizer.convert_tokens_to_ids(txt) for txt in tokenized_texts],
                          maxlen=MAX_LEN, dtype="long", truncating="post", padding="post")
#print(input_ids)

#tokenize test set
tokenized_texts_test = [tokenizer.tokenize(sent) for sent in sentences_test]
print("tokenized_texts_test[0]:")
print(tokenized_texts_test[0])
print()

#encode test set
MAX_LEN_TEST = 116
input_ids_test = pad_sequences([tokenizer.convert_tokens_to_ids(txt) for txt in tokenized_texts_test],
                          maxlen=MAX_LEN_TEST, dtype="long", truncating="post", padding="post")
print("This is input_ids_test: ")
print(input_ids_test)
print()

"""# Labels encoding"""

tags = pad_sequences([[tag2idx.get(l) for l in lab] for lab in labels],
                     maxlen=MAX_LEN, value=tag2idx["O"], padding="post",
                     dtype="long", truncating="post")
#print(tags)
#print(len(tags))

#make fake tags, length of test = 1439
tags_test = pad_sequences([[tag2idx.get(l) for l in lab] for lab in labels_test],
                     maxlen=MAX_LEN_TEST, value=tag2idx["O"], padding="post",
                     dtype="long", truncating="post")

#print(tags_test)
#print(len(tags_test))

"""# Mask in input_ids"""

#attention mask for train set
attention_masks = [[float(i>0) for i in ii] for ii in input_ids]

#attention mask for test set
attention_masks_test = [[float(i>0) for i in ii] for ii in input_ids_test]

#split data ##maynot need to do this
#tr_inputs, val_inputs, tr_tags, val_tags = train_test_split(input_ids, tags, 
#                                                            random_state=2018, test_size=0.1)
#tr_masks, val_masks, _, _ = train_test_split(attention_masks, input_ids,
#                                             random_state=2018, test_size=0.1)

#print("tr_tags", tr_tags)

#transfer train/dev data to tensor
tr_inputs = torch.tensor(input_ids)
val_inputs = torch.tensor(input_ids_test)
tr_tags = torch.tensor(tags)
val_tags = torch.tensor(tags_test) #no tag for dev data
tr_masks = torch.tensor(attention_masks)
val_masks = torch.tensor(attention_masks_test)

#transfer train/dev data, tensor to dataloader
train_data = TensorDataset(tr_inputs, tr_masks, tr_tags)
train_sampler = RandomSampler(train_data)
train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=batch_size)

valid_data = TensorDataset(val_inputs, val_masks, val_tags)
valid_sampler = SequentialSampler(valid_data)
valid_dataloader = DataLoader(valid_data, sampler=valid_sampler, batch_size=batch_size)

model = BertForTokenClassification.from_pretrained("bert-base-uncased", num_labels=len(tag2idx))

FULL_FINETUNING = True
if FULL_FINETUNING:
    param_optimizer = list(model.named_parameters())
    no_decay = ['bias', 'gamma', 'beta']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)],
         'weight_decay_rate': 0.01},
        {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)],
         'weight_decay_rate': 0.0}
    ]
else:
    param_optimizer = list(model.classifier.named_parameters()) 
    optimizer_grouped_parameters = [{"params": [p for n, p in param_optimizer]}]
optimizer = Adam(optimizer_grouped_parameters, lr=3e-5)

from seqeval.metrics import f1_score

def flat_accuracy(preds, labels):
    pred_flat = np.argmax(preds, axis=2).flatten()
    labels_flat = labels.flatten()
    return np.sum(pred_flat == labels_flat) / len(labels_flat)

epochs = 15
max_grad_norm = 1.0

for _ in trange(epochs, desc="Epoch"):
    # TRAIN loop
    model.train()
    tr_loss = 0
    nb_tr_examples, nb_tr_steps = 0, 0
    for step, batch in enumerate(train_dataloader):
        # add batch to gpu
        #batch = tuple(t.to(device) for t in batch)
        b_input_ids, b_input_mask, b_labels = batch
        # forward pass
        loss = model(b_input_ids, token_type_ids=None,
                     attention_mask=b_input_mask, labels=b_labels)
        # backward pass
        loss.backward()
        # track train loss
        tr_loss += loss.item()
        nb_tr_examples += b_input_ids.size(0)
        nb_tr_steps += 1
        # gradient clipping
        torch.nn.utils.clip_grad_norm_(parameters=model.parameters(), max_norm=max_grad_norm)
        # update parameters
        optimizer.step()
        model.zero_grad()
    # print train loss per epoch
    print("Train loss: {}".format(tr_loss/nb_tr_steps))
    # VALIDATION on validation set
    model.eval()
    eval_loss, eval_accuracy = 0, 0
    nb_eval_steps, nb_eval_examples = 0, 0
    predictions , true_labels = [], []
    for batch in valid_dataloader:
        #batch = tuple(t.to(device) for t in batch)
        b_input_ids, b_input_mask, b_labels = batch
        
        with torch.no_grad():
            tmp_eval_loss = model(b_input_ids, token_type_ids=None,
                                  attention_mask=b_input_mask, labels=b_labels)
            logits = model(b_input_ids, token_type_ids=None,
                           attention_mask=b_input_mask)
        logits = logits.detach().cpu().numpy()
        label_ids = b_labels.to('cpu').numpy()
        predictions.extend([list(p) for p in np.argmax(logits, axis=2)])
        true_labels.append(label_ids)
        
        tmp_eval_accuracy = flat_accuracy(logits, label_ids)
        
        eval_loss += tmp_eval_loss.mean().item()
        eval_accuracy += tmp_eval_accuracy
        
        nb_eval_examples += b_input_ids.size(0)
        nb_eval_steps += 1
    eval_loss = eval_loss/nb_eval_steps
    print("Validation loss: {}".format(eval_loss))
    print("Validation Accuracy: {}".format(eval_accuracy/nb_eval_steps))
    pred_tags = [tags_vals[p_i] for p in predictions for p_i in p]
    valid_tags = [tags_vals[l_ii] for l in true_labels for l_i in l for l_ii in l_i]
    print("F1-Score: {}".format(f1_score(pred_tags, valid_tags)))

# saving the entire model
#torch.save(model, 'entire_model_test.pt')

# loading the entire model
#model_new = torch.load('entire_model_test.pt')

########not sure about this code
#save model before model evaluation
#Save&Load Model for Inference
#PATH_p = "/home/users0/changwn/nlu_project/large/model_para/" #this path does not work
#torch.save(model.state_dict(), PATH_p) 
#the_model = TheModelClass(*args, **kwargs)
#the_model.load_state_dict(torch.load(PATH_p))

#Save/Load Entire Model
#PATH_c = "/home/users0/changwn/nlu_project/large/model_complete/"
#torch.save(model, PATH_c) 
#the_model = torch.load(PATH_c)

model.eval()
test_sentences = []
predictions = []
true_labels = []
eval_loss, eval_accuracy = 0, 0
nb_eval_steps, nb_eval_examples = 0, 0
for batch in valid_dataloader:
    #batch = tuple(t.to(device) for t in batch)
    b_input_ids, b_input_mask, b_labels = batch
    #print(b_input_ids)
    #print(b_input_mask)
    #print("this true label: ", b_labels)

    with torch.no_grad():
        tmp_eval_loss = model(b_input_ids, token_type_ids=None,
                              attention_mask=b_input_mask, labels=b_labels)
        logits = model(b_input_ids, token_type_ids=None,
                       attention_mask=b_input_mask)
        
    logits = logits.detach().cpu().numpy()
    predictions.extend([list(p) for p in np.argmax(logits, axis=2)])

    label_ids = b_labels.to('cpu').numpy()
    true_labels.append(label_ids)

    test_ids = b_input_ids.to('cpu').numpy()
    test_sentences.append(test_ids) ##

    tmp_eval_accuracy = flat_accuracy(logits, label_ids)

    eval_loss += tmp_eval_loss.mean().item()
    eval_accuracy += tmp_eval_accuracy

    nb_eval_examples += b_input_ids.size(0)
    nb_eval_steps += 1

pred_tags = [[tags_vals[p_i] for p_i in p] for p in predictions]
valid_tags = [[tags_vals[l_ii] for l_ii in l_i] for l in true_labels for l_i in l ]
print("Validation loss: {}".format(eval_loss/nb_eval_steps))
print("Validation Accuracy: {}".format(eval_accuracy/nb_eval_steps))
print("Validation F1-Score: {}".format(f1_score(pred_tags, valid_tags)))

print()
print("This is pred_tag: ", pred_tags)
print()
print("This is num of pred_tags set (should be 2887): ", len(pred_tags))
print()
print("This is length of first pred_tag: ", len(pred_tags[0]))
print()
i = 0
for t in pred_tags:
  print("This is ", str(i),  " pred_tag: ", t)
  i += 1

df_test["pred_tags"] = pred_tags
df_test.to_json(r'/home/users0/changwn/nlu_project/large/test_pred_e15.json')





