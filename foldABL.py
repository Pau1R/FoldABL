import os
import shutil
import sublime
import sublime_plugin
import datetime
import re

def replace_comments (text): # replace all comment symbols with dots
    st_pos = []
    end_pos = []
    comment_pairs = []

    # getting a list of text positions of start and end comment tags 
    for m in re.finditer("/\*", text, re.IGNORECASE):
        st_pos.append(m.start())
    for m in re.finditer("\*/", text, re.IGNORECASE):
        end_pos.append(m.end())

    # forming pairs of comment blocks
    for elem in st_pos:
        cow = 1
        next = elem
        for num in range(len(st_pos[st_pos.index(next):]) + len(end_pos)):
            next, type = get_next_position(st_pos[st_pos.index(elem):], end_pos, next)
            if type == 1:
                cow = cow + 1
            else:
                cow = cow - 1
            if cow == 0 and next != 9999999:
                end_val = end_pos[end_pos.index(next)]
                comment_pairs.append((elem, end_val))
                break

    # within each comment block replace comments with dots
    for comment in comment_pairs:
        text = text[:comment[0]] + '.' * (comment[1] - comment[0]) + text[comment[1]:]
    return text

# get closest next value from two lists
def get_next_position (open, close, current):
    x = 0
    y = 0
    for elem in open:
        if elem > current:
            x = open[open.index(elem)]
            break
        if x == 0:
            x = 9999999
    for elem in close:
        if elem > current:
            y = close[close.index(elem)]
            break
        if y == 0:
            y = 9999999
    if x < y:
        return x, True
    else:
        return y, False


def getPairs(self, operation_type):
    text = self.view.substr(sublime.Region(0, self.view.size()))
    st_pos = []
    end_pos = []
    pairs = []

    # regular expressions defining the block opening and closing tags
    start_regexr = (
        "("
            "do((.{1,50}TO.{1,50})|)|"
            "do {1,10}while.{1,100}|"
            "[^b]lock|"
            "\nmain-block|"
            "error|"
            "transaction|"
            "function {1,10}\S{1,100} {1,10}return(s| )(.|\n| ){1,2000}?|"
            "repeat.{0,10}|"
            "finally.{0,10}|"
            "for (each|first|last)(.|\n){1,1000}?|"
            "case {1,10}(\S|[^ ,/'{}\[\])]){1,100}|"
            "procedure {1,10}(.){1,500}"
        ") {0,10}:")

    start_regexes = (
        "do((.{1,50}TO.{1,50})|) {0,10}:",
        "do {1,10}while.{1,100} {0,10}:",
        "[^b]lock {0,10}:",
        "\nmain-block {0,10}:",
        "error {0,10}:",
        "transaction {0,10}:",
        "function {1,10}\S{1,100} {1,10}return(s| )(.|\n){1,2000}? {0,10}:",
        "repeat.{0,10} {0,10}:",
        "finally.{0,10} {0,10}:",
        "for (each|first|last)(.|\n){1,1000}? {0,10}:",
        "case {1,10}(\S|[^ ,/'{}\[\])]){1,100} {0,10}:",
        "procedure {1,10}(.){1,500} {0,10}:")

    end_regex = (
        "( |\n){1,10}"
        "end( {0,10}(" 
            "procedure|"
            "case|"
            "function|"
            "finally|)"
        ")\.(|\n)")


    text = replace_comments(text)

    # form a list of block opening and closing tags
    for start_regex in start_regexes:
        for m in re.finditer(start_regex, text, re.IGNORECASE):
           st_pos.append(m.end())
    for m in re.finditer(end_regex, text, re.IGNORECASE):
            end_pos.append(m.end())

    # sorting in alphabetical order
    st_pos.sort()

    # forming pairs of text blocks
    for elem in st_pos:
        cow = 1
        next = elem
        for num in range(len(st_pos[st_pos.index(next):]) + len(end_pos)):
            next, type = get_next_position(st_pos[st_pos.index(elem):], end_pos, next)
            if type == 1:
                cow = cow + 1 # for each opening tag
            else:
                cow = cow - 1 # for each closing tag
            if cow == 0 and next != 9999999: # a pair of tags is found when the amount of opening and closing tags are the same
                end_val = end_pos[end_pos.index(next)]
                pairs.append((elem, end_val))
                break

    # fold block
    selection = self.view.sel()[0]
    # if self.view.is_folded(selection):
    #print (not self.view.is_folded(selection))
    if operation_type == 1:
        operation_on_selected_region(selection, pairs, self.fold)
    if operation_type == 2:
        operation_on_selected_region(selection, pairs, self.unfold)
        operation_on_selected_region(selection, pairs, self.highlight)
    if operation_type == 3:
        operation_on_selected_region(selection, pairs, self.highlight)

def operation_on_selected_region(selection, fold_regions, operation):
    closest_value = []
    minimal_value = 9999999
    for fold_region in fold_regions:
        if fold_region[0] <= selection.begin() and fold_region[1] >= selection.end():
            if fold_region[1] - fold_region[0] < minimal_value:
                minimal_value = fold_region[1] - fold_region[0]
                closest_value = fold_region

    content = [sublime.Region(fold_regions[fold_regions.index(closest_value)][0], 
                              fold_regions[fold_regions.index(closest_value)][1])]
    operation(content)


class FoldCommands(sublime_plugin.TextCommand):

    def fold(self, regions):
        if len(regions) > 0:
            self.view.fold(regions)

    def unfold(self, regions):
        new_sel = []
        for s in self.view.sel():
            unfold = s
            if s.empty():
                unfold = sublime.Region(s.a - 1, s.a + 1)

            unfolded = self.view.unfold(unfold)
            if len(unfolded) == 0 and s.empty():
                unfolded = self.view.unfold(self.view.full_line(s.b))

            if len(unfolded) == 0:
                new_sel.append(s)
            else:
                for r in unfolded:
                    new_sel.append(r)

    def highlight(self, regions):
        if len(regions) > 0:
            self.view.sel().clear()
            for r in regions:
                self.view.sel().add(r)  


class AblFoldCommand(FoldCommands):

    def run(self, edit):
        getPairs(self, 1) # fold region

class AblUnfoldCommand(FoldCommands):

    def run(self, edit):
        getPairs(self, 2) # unfold region

class AblHighlightCommand(FoldCommands):

    def run(self, edit):
        getPairs(self, 3) # highlight region