#!/usr/bin/python
"""Script for managing goals."""

import os
import sys
import decimal
import json
import time
import glob
import datetime

INPUT_SEPARATOR = ","
NOW = decimal.Decimal(str(time.time()))

one_day_in_seconds = decimal.Decimal(24*60*60)
one_week_in_seconds = 14*one_day_in_seconds

# class ActivityLog:
  # FILE_NAME = "activity.log"
  
  # def __init__(self):
    # self.data = []
    
  # @staticmethod
  # def load():
    # log = ActivityLog()
    # inFile = open(ActivityLog.FILE_NAME, "rb")
    # log.data = json.loads(inFile.read(), parse_float=decimal.Decimal, parse_int=decimal.Decimal)
    # inFile.close()
    # return log
    
  # def save(self):
    # outFile = open(ActivityLog.FILE_NAME, "wb")
    # outFile.write(json.dumps(self.data, default=_serializer, sort_keys=True, indent=2))
    # outFile.close()
    
  # def pop(self):
    # self.data.pop()
    # self.save()
    
  # def add(self, newData):
    # self.data.append(newData)
    # self.save()

def prompt(message):
  print(message)
  return raw_input()
  
def read_map(message):
  data = {}
  secondary_separator = ";"
  default_key = "default"
  def read_min_max(next_data):
    if secondary_separator in next_data:
      next_data = next_data.split(secondary_separator)
    else:
      next_data = [next_data, next_data]
    next_data[0] = decimal.Decimal(next_data[0])
    next_data[1] = decimal.Decimal(next_data[1])
    return next_data
  while True:
    user_data = prompt(message)
    if not user_data:
      return data
    if INPUT_SEPARATOR not in user_data:
      assert default_key not in data
      next_data = user_data.strip()
      data[default_key] = read_min_max(next_data)
      #NOTE:  short circuiting this because it's rare that you would want to put no message and then some message
      return data
    else:
      split_data = user_data.split(INPUT_SEPARATOR)
      assert len(split_data) == 2
      data[split_data[0].strip()] = read_min_max(split_data[1].strip())
  return data
      
def _convert_values_to_decimal(data):
  for key in data:
    #TODO:  remove this once everything is converted
    if isinstance(data[key], list):
      newVal = [decimal.Decimal(data[key][0]), decimal.Decimal(data[key][1])]
    else:
      newVal = [decimal.Decimal(data[key]), decimal.Decimal(data[key])]
    data[key] = newVal
    
def _serializer(object):
  if isinstance(object, decimal.Decimal):
    return str(object)
  else:
    return json.dumps(object)
    
def parse_time_from_user(user_data, last_recorded_time):
  #figure out how long it took, in seconds
  duration = None
  user_data = user_data.strip()
  if user_data:
    duration = user_data
    if ':' in duration:
      data = duration.strip().split(':')
      if len(data) == 3:
        days, hour, minute = data
      else:
        days = 0
        hour, minute = data
      days_ago = int(days)
      hour = int(hour)
      minute = int (minute)
      localTime = time.localtime()
      hours_ago = (localTime.tm_hour - hour) + (days_ago * 24)
      minutes_ago = (localTime.tm_min - minute) + (hours_ago * 60)
      assert minutes_ago > 0, "Cant record into the future"
      duration = -1 * minutes_ago * 60
    else:
      duration = int(duration) * 60
    #negative numbers mean that happened until x minutes ago
    if duration < 0:
      duration = (NOW - last_recorded_time) + duration
  if not duration:
    duration = NOW - last_recorded_time
  return duration

def load_all_goals():
  goals = {}
  for file_name in glob.glob("goals/*.json"):
    file_name = file_name.replace("\\", "/")
    goal = Goal.load_from_file(file_name)
    goals[goal.id] = goal
  return goals
  
def parse_goal_from_user(user_data, goals):
  user_data = user_data.strip()
  #first try to find by goal id
  try:
    user_data =  int(user_data)
    return goals[user_data]
  #then look for goal name
  except ValueError:
    user_data = user_data.lower()
    possible_goals = [goal for goal in goals.values() if user_data in goal.title]
    exact_goals = [goal for goal in possible_goals if goal.title == user_data]
    if len(exact_goals) == 1:
      return exact_goals[0]
    if len(possible_goals) == 1:
      return possible_goals[0]
    assert len(possible_goals) > 0, "Could not find any goals with that text."
    #hmm, user was ambiguous.  Ask them to clarify:
    goal_choice = prompt("\n".join([str(i)+". "+possible_goals[i] for i in range(0,len(possible_goals))]))
    return possible_goals[int(goal_choice.strip())]

class Goal:
  ID_FILE = "goals/next.id"
  THOUGHT_SEPARATOR = "*********************************"

  @staticmethod
  def get_next_id():
    inFile = open(Goal.ID_FILE, "rb")
    nextId = int(inFile.read().strip())
    inFile.close()
    return nextId
  
  @staticmethod  
  def increment_next_id():
    nextId = Goal.get_next_id()
    nextId += 1
    outFile = open(Goal.ID_FILE, "wb")
    outFile.write(str(nextId))
    outFile.close()
  
  def __init__(self):
    self.id = None
    self.description = ""
    self.thoughts = ""
    self.tags = []
    self.value_components = {}
    self.cost_components = {}
    self.time_components = {}
    self.completed_at = None
    self.created_at = None
    self.last_saved_at = None
    self.progress = []
    self.requires = []
    
  @staticmethod
  def file_name_from_id(file_id):
    return "goals/"+str(file_id)+".json"
    
  @staticmethod
  def load_from_file(file_name):
    #file_name = Goal.file_name_from_id(file_id)
    in_file = open(file_name, "rb")
    data = in_file.read()
    in_file.close()
    goal = Goal()
    thoughts, jsonData = data.split(Goal.THOUGHT_SEPARATOR)
    obj = json.loads(jsonData)
    #copy all the keys from obj to us
    for key in obj:
      setattr(goal, key, obj[key])
    goal.thoughts = thoughts.strip()
    goal._finish_load()
    return goal
    
  def load_from_user(self, tags):
    self.created_at = NOW
    #get the next highest id automatically
    self.id = Goal.get_next_id()
    #assign tags automatically from the interface
    self.tags = tags
    #read a description
    self.description = prompt("Enter a description:")
    #read value estimates
    #self.value_components = read_map("Enter values(reason, $[lower];$[upper]):")
    self.value_components = {"default": ["1", "1"]}
    #read cost estimates (if any)
    #self.cost_components = read_map("Enter costs (reason, $[lower];$[upper]):")
    self.cost_components = {}
    #read time estimates
    #self.time_components = read_map("Enter times (description, minutes[lower];minutes[upper]):")
    self.time_components = {"default": ["1", "1"]}
    #TODO:  someday go put this back, too complicated for now
    ##read pre-requisite tasks if any are required
    #requiredTaskIdStr = prompt("Enter required tasks (if any):")
    #if requiredTaskIdStr:
    #  self.requires = [int(r) for r in requiredTaskIdStr.split(",")]
    self.requires = []
    # #read extra data (mark as completed, extra tags?, whatever else is there but rare)
    # extra_data = prompt("Extra data (is complete, extra tags)").split(INPUT_SEPARATOR)
    # is_complete = extra_data.pop(0)
    # if is_complete == '1':
    #   self.completed_at = NOW
    #convert the strings we read in into Decimals
    self._finish_load()
    #save the goal
    self.save()
    Goal.increment_next_id()
    
  def save(self):
    """Serialize mostly to JSON.  Have to handle Decimals specially, and the thoughts field, which I want to be directly editable text"""
    self.last_saved_at = NOW
    thoughts = self.thoughts
    self.thoughts = ""
    data = thoughts+"\n"+Goal.THOUGHT_SEPARATOR+"\n"+json.dumps(self.__dict__, default=_serializer, sort_keys=True, indent=2)
    self.thoughts = thoughts
    outFile = open(Goal.file_name_from_id(self.id), 'wb')
    outFile.write(data)
    outFile.close()
    
  def _finish_load(self):
    _convert_values_to_decimal(self.value_components)
    _convert_values_to_decimal(self.cost_components)
    _convert_values_to_decimal(self.time_components)
    real_progress = []
    for data in self.progress:
      if len(data) == 2:
        data.append(1)
      if len(data) == 3:
        data.append("")
      start, end, focus, notes = data
      real_progress.append([decimal.Decimal(start), decimal.Decimal(end), decimal.Decimal(focus), notes])
    self.progress = real_progress
    self.created_at = decimal.Decimal(self.created_at)
    if self.last_saved_at:
      self.last_saved_at = decimal.Decimal(self.last_saved_at)
    if self.completed_at:
      self.completed_at = decimal.Decimal(self.completed_at)
    
  def add_time(self, start_time, end_time, focus, notes, is_complete):
    #put a new entry into progress
    self.progress.append([start_time, end_time, focus, notes])
    if is_complete:
      self.completed_at = NOW
    ##put a new entry into our log
    # log = ActivityLog.load()
    # log.add([self.id, start_time, end_time])
    self.save()
    
  def undo_add_time(self):
    #this happens when the user inputs an incorrect value
    #pop the last entry off our time stack.  
    self.progress.pop()
    ##also update the activity log
    # log = ActivityLog.load()
    # log.pop()
    self.save()
    
  def get_effort_in_interval(self, start_time, end_time):
    total_effort = decimal.Decimal(0)
    for start, end, focus, notes in self.progress:
      if end < start_time:
        end = start_time
      effort = end - start
      if effort < 0:
        continue
      total_effort += effort * focus
    return total_effort
    
  @property
  def last_updated_at(self):
    if len(self.progress) <= 0:
      return None
    else:
      return self.progress[-1][1]
    
  @property
  def total_estimated_cost(self):
    return sum([(r[0]+r[1])/2 for r in self.cost_components.values()])
    
  @property
  def total_estimated_value(self):
    return sum([(r[0]+r[1])/2 for r in self.value_components.values()])
    
  @property
  def total_estimated_time(self):
    return sum([(r[0]+r[1])/2 for r in self.time_components.values()])
    
  @property
  def net_estimated_value(self):
    return self.total_estimated_value - self.total_estimated_cost
    
  @property
  def value_rate(self):
    return self.net_estimated_value / self.total_estimated_time
    
  @property
  def title(self):
    return self.description.split('.')[0]
  
  @property
  def is_complete(self):
    return self.completed_at != None
    
def create_goal(user_data, tags):
  goal = Goal()
  goal.load_from_user(tags)
  goal.save()
  
def add_time(user_data, goal_dict, prev_entry):
  user_data = user_data.strip()
  is_complete = False
  if prev_entry == None:
    last_recorded_time = decimal.Decimal("1339427450.91")
  else:
    last_recorded_time = prev_entry.end_time
  goal_amount_pairs = []
  end_time = None
  #handle special cases:
  notes = ""
  if INPUT_SEPARATOR not in user_data:
    end_time = NOW
    #they provided neither of the arguments.  Just append time to the last goal.
    if not user_data:
      goal_amount_pairs = prev_entry.get_goal_amount_pairs()
    #they provided only one of the arguments. For now we assume it was the goal
    else:
      goal_data = user_data
  else:
    data = user_data.split(INPUT_SEPARATOR)
    if len(data) == 2:
      goal_data, time_data = data
    elif len(data) == 3:
      goal_data, time_data, notes = data
    else:
      goal_data, time_data, notes, is_complete = data
      is_complete = is_complete == '1'
  notes = notes.strip()
  if not goal_amount_pairs:
    if '/' in goal_data:
      goal_data_list = goal_data.split('/')
    else:
      goal_data_list = [goal_data]
    for goal_data in goal_data_list:
      if ':' in goal_data:
        goal_name, amount = goal_data.split(":")
      else:
        goal_name = goal_data
        amount = 1
      amount = decimal.Decimal(amount)
      #figure out what goal the user is referring to
      goal = parse_goal_from_user(goal_name, goal_dict)
      goal_amount_pairs.append([goal, amount])
  if end_time == None:
    #figure out start and end time
    duration = parse_time_from_user(time_data, last_recorded_time)
    end_time = last_recorded_time + duration
  #update the goals
  for goal, amount in goal_amount_pairs:
    goal.add_time(last_recorded_time, end_time, decimal.Decimal(amount), notes, is_complete)
  
def edit(user_data, goal_dict):
  #figure out what goal the user is referring to
  goal = parse_goal_from_user(goal_data, goal_dict)
  #open $EDITOR (notepad++ or emacs) with the right file
  fileName = Goal.file_name_from_id(goal.id)
  os.system(fileName)

def review(goals, user_data):
  """Review everything accomplished today"""
  days_ago = 0
  try:
    days_ago = int(user_data)
  except ValueError:
    pass
  now_date_time = datetime.datetime.fromtimestamp(NOW)
  time_delta = now_date_time - datetime.datetime(now_date_time.year, now_date_time.month, now_date_time.day, 0, 0, 0)
  extra_time = 60 * 60 * 2
  start_time = (NOW - decimal.Decimal(str(time_delta.total_seconds()))) - (days_ago * one_day_in_seconds)
  recent_entries = get_multi_entries_since(goals, start_time - extra_time)
  end_time = start_time + one_day_in_seconds + extra_time
  for entry in recent_entries:
    if entry.end_time < end_time:
      segments = int(round((entry.end_time - entry.start_time) / decimal.Decimal(60.0 * 10.0)))
      print(str(entry) + '\n||'*segments)

def simple_review(goals, user_data):
  """Review everything accomplished today. Prints in format for summarization into daily log"""
  max_days_ago = 0
  try:
    max_days_ago = int(user_data)
  except ValueError:
    pass
  days_ago_list = list(range(0, max_days_ago+1))
  for days_ago in days_ago_list:
    interesting_activities, then_date = get_interesting_activities(goals, days_ago)
    sorted_keys = reversed(sorted(interesting_activities.keys(), key=lambda k: sum([x.duration for x in interesting_activities[k]])))
    print("\n%s/%s/%s\n" % (then_date.month, then_date.day, then_date.year))
    for key in sorted_keys:
      value = interesting_activities[key]
      total_time = int(sum([x.duration for x in value]) / decimal.Decimal(60.0))
      print("%s (%s): %s" % (key, total_time, '. '.join([x.notes for x in value if x.notes])))

def weekly_review(goals, user_data):
  starting_days_ago = int(user_data)
  all_activities = {}
  for days_ago in list(range(max(0, starting_days_ago-7), starting_days_ago)):
    interesting_activities, then_date = get_interesting_activities(goals, days_ago)
    print("\n%s/%s/%s\n" % (then_date.month, then_date.day, then_date.year))
    for description in interesting_activities.keys():
      if description not in all_activities:
        all_activities[description] = []
      value = interesting_activities[description]
      all_activities[description] = all_activities[description] + [(sum([x.duration for x in value]) / decimal.Decimal(3600.0), '. '.join([x.notes for x in value if x.notes]))]
  sorted_keys = reversed(sorted(all_activities.keys(), key=lambda k: sum([x[0] for x in all_activities[k]])))
  for description in sorted_keys:
    daily_entries = all_activities[description]
    total_time = sum([x[0] for x in daily_entries])
    useful_notes = '\n'.join(['        '+x[1] for x in reversed(sorted(daily_entries, key=lambda y: y[0])) if x[1]])
    if useful_notes:
      useful_notes = '\n'+useful_notes
    print('%s (%s):%s' % (description, round(total_time, 1), useful_notes))


def get_interesting_activities(goals, days_ago):
    now_date_time = datetime.datetime.fromtimestamp(NOW)
    time_delta = now_date_time - datetime.datetime(now_date_time.year, now_date_time.month, now_date_time.day, 0, 0, 0)
    extra_time = 60 * 60 * 2
    start_time = (NOW - decimal.Decimal(str(time_delta.total_seconds()))) - (days_ago * one_day_in_seconds)
    recent_entries = get_multi_entries_since(goals, start_time - extra_time)
    end_time = start_time + one_day_in_seconds + extra_time
    interesting_activities = {}
    found_sleep = False
    for entry in recent_entries:
      if entry.end_time < end_time:
        description = entry.description
        if 'sleep' in entry.description:
          found_sleep = True
          continue
        if not found_sleep:
          continue
        if "upkeep" in entry.tags:
          description = 'upkeep'
        if entry.description == 'clean':
          description = 'upkeep'
        if description not in interesting_activities:
          interesting_activities[description] = []
        interesting_activities[description].append(entry)
    then_date = datetime.datetime.fromtimestamp(start_time + extra_time)
    return interesting_activities, then_date

def summarize(goals, user_data, for_tags = False):
  """
  Review everything accomplished in given time period, aggregated by tag and description
  Expected user input: /sum <start_days> <end_days> (or /sumtag)
  """
  # returns total time spent in time period on each tag
  def get_entries_by_tag(entries, start_time, end_time):
    entries_by_tag = {}
    # splits entries in chronological order by tag
    for entry in entries:
      tag = entry.goal.tags[0]
      if tag in entries_by_tag.keys():
        entries_by_tag[tag].append(entry)
      else:
        entries_by_tag[tag] = [entry]
    return entries_by_tag

  # returns total tiem spent in time period on each task type
  def get_entries_by_description(entries, start_time, end_time):
    entries_by_description = {}
    for entry in entries:
      description = entry.goal.description
      if description in entries_by_description.keys():
        entries_by_description[description].append(entry)
      else:
        entries_by_description[description] = [entry]
    return entries_by_description

  def get_duration_for_entries(entries):
    total_duration = 0
    for entry in entries:
      total_duration += entry.duration
    return total_duration

  def get_labels_sorted_by_duration(label_dict):
    labels = list(label_dict.keys())
    labels.sort(key=lambda label: get_duration_for_entries(label_dict[label]),
      reverse=True)
    return labels

  def get_human_readable_duration(duration):
    hours = int(duration / (60*60))
    minutes = int((duration/60) - (hours*60))
    return "%.2d h %.2d min" % (hours, minutes)

  def print_effort(tagged_entries, start_time, end_time, pad_spaces=25):
    total_duration = end_time - start_time
    print("%s : %s" % (pad("Total", pad_spaces), get_human_readable_duration(total_duration)))
    print("-" * (pad_spaces+21))
    for tag in get_labels_sorted_by_duration(tagged_entries):
      total_tag_duration = get_duration_for_entries(tagged_entries[tag])
      print("%s - %s - %0d %%" % (pad(tag, pad_spaces),
        get_human_readable_duration(total_tag_duration), 
        round(100*total_tag_duration/total_duration)))
    print("-" * (pad_spaces+21))
    for tag in get_labels_sorted_by_duration(tagged_entries):
      total_tag_duration = get_duration_for_entries(tagged_entries[tag])
      print("-" * (pad_spaces+21))
      print("- %s - %s - %0d %%" % (pad(tag, pad_spaces-2),
        get_human_readable_duration(total_tag_duration), 
        round(100*total_tag_duration/total_duration)))
      print("-" * (pad_spaces+21))
      for entry in tagged_entries[tag]:
        print(str(entry))

  """Start summarize function"""
  days_ago_start = 0
  days_ago_end = -1
  try:
    day_range = user_data.split(" ")
    days_ago_start = int(day_range[0])
    days_ago_end = days_ago_start-1
    if len(day_range) > 1:
      days_ago_end = int(day_range[1])
  except ValueError:
    pass
  now_date_time = datetime.datetime.fromtimestamp(NOW)
  delta_to_day_start = now_date_time - datetime.datetime(now_date_time.year, now_date_time.month, now_date_time.day, 0, 0, 0)
  start_extra_pad = 60*60 # pad start time by 1 hour to catch sleep
  start_time = (NOW - decimal.Decimal(str(delta_to_day_start.total_seconds()))) - (days_ago_start * one_day_in_seconds) - start_extra_pad
  end_time = (NOW - decimal.Decimal(str(delta_to_day_start.total_seconds()))) - (days_ago_end * one_day_in_seconds)
  recent_entries = get_entries_in_period(goals, start_time, end_time)
  tagged_entries = get_entries_by_tag(recent_entries, start_time, end_time)
  desc_entries = get_entries_by_description(recent_entries, start_time, end_time)

  if for_tags:
    print_effort(tagged_entries, start_time, end_time, pad_spaces=10)
  else:
    print_effort(desc_entries, start_time, end_time, pad_spaces=25)

  
def fancy_tri_column_print(a, b, c, col_width, spacing):
  longest_column = max(len(a), len(b), len(c))
  rowStr = ""
  for title in ("Optimal", "Frequent", "Recent"):
    rowStr += title + " "*(col_width-len(title))
    rowStr += " " * spacing
  print(rowStr.strip())
  for i in range(0, longest_column):
    rowStr = ""
    for col in (a,b,c):
      if len(col) > i:
        goal = col[i]
        header = str(goal.id) + ". "
        headerLen = len(header)
        rowStr += header
        data = goal.title[:col_width-headerLen]
        rowStr += data
        rowStr += " " * (col_width - (len(data) + headerLen))
      else:
        rowStr += " " * col_width
      if col != c:
        rowStr += " " * spacing
    print(rowStr)
  print("")
      
def get_most_recent_goals(goals, limit):
  goals.sort(key=lambda goal: goal.last_updated_at)
  selected_goals = goals[-1*limit:]
  selected_goals.reverse()
  return selected_goals
  
def get_most_frequent_goals(goals, limit, time_limit):
  min_time = NOW - time_limit
  relevant_goals = [goal for goal in goals if goal.last_updated_at > min_time]
  relevant_goals.sort(key=lambda goal: goal.get_effort_in_interval(min_time, NOW))
  relevant_goals.reverse()
  return relevant_goals[:limit]
  
def get_optimal_goals(goals, limit):
  goals.sort(key=lambda goal: goal.value_rate)
  goals.reverse()
  return goals[:limit]

def pad(data, maxLen):
      if len(data) < maxLen:
        return data + " " * (maxLen - len(data))
      return data[:maxLen]
  
class Entry():
  def __init__(self, progress_data, goal):
    self.start_time = progress_data[0]
    self.end_time = progress_data[1]
    self.focus = 1
    if len(progress_data) > 2:
      self.focus = progress_data[2]
    self.notes = ""
    if len(progress_data) > 3:
      self.notes = progress_data[3]
    else:
      self.notes = ""
    self.duration = self.end_time - self.start_time
    self.goal = goal

  @property
  def description(self):
    return self.goal.description

  @property
  def tags(self):
    return self.goal.tags

  def __str__(self):
    formatted_starttime = datetime.datetime.fromtimestamp(self.start_time).strftime("%m-%d %H:%M")
    formatted_endtime = datetime.datetime.fromtimestamp(self.end_time).strftime("%H:%M")
    hours = int(self.duration / (60*60))
    minutes = int((self.duration/60) - (hours*60))
    tag_set = set(self.goal.tags)
    tag_string = pad("|".join(tag_set), 10)
    return "[%s] %s to %s (for %.2d:%.2d) %s" % (tag_string, formatted_starttime, formatted_endtime, hours, minutes, self.goal.description)  + ': ' + self.notes

class MultiEntry():
  def __init__(self, entry):
    self.entries = [entry]
    self.start_time = entry.start_time
    self.end_time = entry.end_time
    self.duration = entry.duration
    
  def is_same_time(self, entry):
    return self.start_time == entry.start_time and self.end_time == entry.end_time
    
  def add(self, entry):
    self.entries.append(entry)

  @property
  def description(self):
    return '|'.join([entry.goal.description for entry in self.entries])

  @property
  def tags(self):
    tags = []
    for entry in self.entries:
      tags += entry.goal.tags
    return tags

  @property
  def notes(self):
    return '|'.join([entry.notes for entry in self.entries])
    
  def get_goal_amount_pairs(self):
    goal_amount_pairs = []
    for entry in self.entries:
      goal_amount_pairs.append([entry.goal, entry.focus])
    return goal_amount_pairs
    
  def __str__(self):
    def pad(data, maxLen):
      if len(data) < maxLen:
        return data + " " * (maxLen - len(data))
      return data[:maxLen]
    formatted_starttime = datetime.datetime.fromtimestamp(self.start_time).strftime("%m-%d %H:%M")
    formatted_endtime = datetime.datetime.fromtimestamp(self.end_time).strftime("%H:%M")
    hours = int(self.duration / (60*60))
    minutes = int((self.duration/60) - (hours*60))
    tag_set = set()
    for entry in self.entries:
      tag_set = tag_set.union(set(entry.goal.tags))
    tag_string = pad("|".join(tag_set), 10)
    descriptions = " and ".join([entry.goal.description[:40] for entry in self.entries])
    return "[%s] %s to %s (for %.2d:%.2d) %s" % (tag_string, formatted_starttime, formatted_endtime, hours, minutes, descriptions)  + ': ' + entry.notes
    
def get_multi_entries_since(goals, start_time):
  recent_goals = []
  for goal in goals:
    if goal.last_updated_at == None:
      continue
    if goal.last_updated_at > start_time:
      recent_goals.append(goal)
  entries = []
  for goal in recent_goals:
    for entry in goal.progress:
      entries.append(Entry(entry, goal))
  entries.sort(key=lambda x: x.start_time)
  #now merge Entry's that happened at the same time:
  final_entries = []
  for entry in entries:
    if entry.start_time <= start_time:
      continue
    if len(final_entries) <= 0:
      final_entries.append(MultiEntry(entry))
    prev_entry = final_entries[-1]
    if prev_entry.is_same_time(entry):
      prev_entry.add(entry)
    else:
      final_entries.append(MultiEntry(entry))
  return final_entries

def get_entries_in_period(goals, start_time, end_time):
  recent_goals = []
  for goal in goals:
    if goal.last_updated_at == None:
      continue
    if goal.last_updated_at > start_time:
      recent_goals.append(goal)
  entries = []
  for goal in recent_goals:
    for entry in goal.progress:
      entry_object = Entry(entry, goal)
      if entry_object.start_time >= start_time and entry_object.end_time <= end_time:
        entries.append(entry_object)
  entries.sort(key=lambda x: x.start_time)
  return entries
  
def display_record(entries):
  print("\n".join([str(entry) for entry in entries]) + "\n")

def handle_command_line_data(command_data):
  commands = command_data.split('#')
  for command in commands:
    goal_dict = load_all_goals()
    goals = list(goal_dict.values())
    all_recent_goals = get_most_recent_goals(goals, NUM_TO_SHOW)
    recent_entries = get_multi_entries_since(all_recent_goals, NOW - one_week_in_seconds)
    display_record(recent_entries[-1*NUM_TO_SHOW:])
    prev_entry = recent_entries[-1]
    add_time(command, goal_dict, prev_entry)
    all_recent_goals = get_most_recent_goals(goals, NUM_TO_SHOW)
    recent_entries = get_multi_entries_since(all_recent_goals, NOW - one_day_in_seconds)
    display_record(recent_entries[-10:])

NUM_TO_SHOW = 40

def main():
  #this should only happen on windows
  if os.name == 'nt':
    os.system("mode con cols=190 lines=60")
  # big hack to read string from the command line
  if len(sys.argv) > 0 and sys.argv[1] == '-c':
    handle_command_line_data(sys.argv[2])
    return
  #read tags from args
  tags = sys.argv[1:]
  tag_set = set(tags)
  print(" ".join(tag_set) + "\n=======================================")
  #load all goals
  goal_dict = load_all_goals()
  goals = goal_dict.values()
  #figure out and display the most recent
  all_recent_goals = get_most_recent_goals(goals, NUM_TO_SHOW)
  recent_entries = get_multi_entries_since(all_recent_goals, NOW - one_week_in_seconds)
  display_record(recent_entries[-1*NUM_TO_SHOW:])
  if len(recent_entries) > 0:
    prev_entry = recent_entries[-1]
  #use tags to more sensibly display the most recent tasks, most frequent tasks, and highest value tasks
  if len(tag_set) > 0:
    relevant_goals = [goal for goal in goals if tag_set.issubset(set(goal.tags))]
  else:
    relevant_goals = goals
  recent_goals = get_most_recent_goals(relevant_goals, NUM_TO_SHOW)
  relevant_incomplete_goals = [goal for goal in goals if not goal.is_complete]
  frequent_goals = get_most_frequent_goals(relevant_incomplete_goals, NUM_TO_SHOW, one_week_in_seconds)
  optimal_goals = get_optimal_goals(relevant_incomplete_goals, NUM_TO_SHOW)
  #display 3 columns (60 chars each), one for each of the categories
  fancy_tri_column_print(optimal_goals, frequent_goals, recent_goals, 60, 4)
  #read command and handle
  user_data = prompt("Enter command:")
  if len(user_data) > 0 and user_data[0] == '/':
    command = user_data.split(" ")[0]
    user_data = " ".join(user_data.split(" ")[1:])
    #this command is handled specially in the outer loop, it is the default
    if command != "/add_time":
      if command == "/create":
        create_goal(user_data, tags)
      elif command == "/undo":
        for entry in prev_entry.entries:
          entry.goal.undo_add_time()
      elif command == "/edit":
        edit(user_data, goal_dict)
      elif command == "/review":
        review(goals, user_data)
      elif command == "/simple":
        simple_review(goals, user_data)
      elif command == "/weekly":
        weekly_review(goals, user_data)
      elif command == "/sum":
        summarize(goals, user_data)
      elif command == "/sumtag":
        summarize(goals, user_data, for_tags = True)
      return
  #handle the default case (add_time)
  add_time(user_data, goal_dict, prev_entry)
  #then redisplay recent tasks, because it's nice to see  :)
  all_recent_goals = get_most_recent_goals(goals, NUM_TO_SHOW)
  recent_entries = get_multi_entries_since(all_recent_goals, NOW - one_day_in_seconds)
  display_record(recent_entries[-10:])
  #finally, prompt for any input so that the window doesnt close instantly
  raw_input()
    
if __name__ == "__main__":
  main()
  
