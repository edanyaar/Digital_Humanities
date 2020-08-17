import re
import json
import jsonpickle


# regular expression for the entries in the family tree list version
entry = re.compile(r"\n*(\s*(\d|\+)\s?(\D+)\s?(\d+)?\s?-?\s?(\d+)?\s?ID Number:? #?\s?(\d+\s?B?))\n*")
tree_entry = re.compile(r"\n(.*)\n")


class Place:
    def __init__(self, name, lat, long, wiki_data_id):
        self.name = name
        self.lat = lat
        self.long = long
        self.wiki_data_id = wiki_data_id


class Person:
    def __init__(self, name, id_number, birth_date, death_date):
        self.name = name
        self.surname = name.split()[-1]
        if "(" in self.surname:
            self.surname = " ".join(name.split()[-2:])
            self.given_name = " ".join(name.split()[0:len(name.split()) - 2])
        else:
            self.given_name = " ".join(name.split()[0:len(name.split())-1])
        self.id_number = id_number
        self.birth_place = None
        if birth_date != "0000":
            self.birth_date = birth_date
        else:
            self.birth_date = None
        self.death_date = death_date
        self.death_place = None
        self.burial_place = None
        self.spouse = None
        self.gender = None
        self.children = list()

    def add_spouse(self, spouse):
        self.spouse = spouse

    def add_child(self, child):
        self.children.append(child)

    def add_birth_place(self, name, lat, long, wiki_data_id):
        self.birth_place = Place(name, lat, long, wiki_data_id)

    def add_birth_date(self, birth_date):
        self.birth_date = birth_date

    def add_death_date(self, death_date):
        self.death_date = death_date

    def add_death_place(self, name, lat, long, wiki_data_id):
        self.death_place = Place(name, lat, long, wiki_data_id)

    def add_burial_place(self, name, lat, long, wiki_data_id):
        self.burial_place = Place(name, lat, long, wiki_data_id)

    def add_gender(self, gender):
        self.gender = gender


def parse():
    """
    transform the family tree into GEDCOM format
    """
    with open("familyList.txt", mode='r', encoding="UTF-8") as fl:
        with open("familyTree.txt", mode='r', encoding="UTF-8") as ft:
            with open("familyTree.json", "w+",  encoding="UTF-8") as jsn:
                family_list = fl.read()
                family_tree = ft.read()
                parse_family_tree(family_tree)
                progenitor = parse_familyList(family_list)
                progenitor = update_family_tree(progenitor)
                #jsn.write(json.dumps(json.loads(jsonpickle.encode(progenitor)), indent=4))
                tree_to_gedcom(progenitor)


def parse_familyList(family_list):
    """
    split family list into entries and call parse_familyBranch
    :param family_list: a txt file of the scan of tree in list form
    :return: an object containing the family tree
    """
    l = (re.split(entry, family_list))[1::]
    people = list(zip(*[l[i::7] for i in range(7)]))
    (_, level, name, birth_year, death_year, id_number, _) = people[0]
    progenitor = Person(name,id_number.replace(" ", "").strip(),birth_year,death_year)
    parse_familyBranch(people[1::], 1, progenitor)
    return progenitor


def parse_familyBranch(people, prev_lvl, prev_pers):
    """
    recursively add each family member in the list to the tree
    :param people: a list of the remaining people to be added to the tree
    :param prev_lvl: the indent of the last person to be added to the tree
    :param prev_pers: the last person to be added to the tree
    :return: a person object containing the family tree as derived from the list
    """
    (_, level, name, birth_year, death_year, id_number, _) = people[0]
    cur_pers = Person(name,id_number.replace(" ", "").strip(),birth_year,death_year)
    if level == "+":
        prev_pers.add_spouse(cur_pers)
        people = people[1::]
        if people:
            (_, level, name, birth_year, death_year, id_number, _) = people[0]
            cur_pers = Person(name, id_number.replace(" ", "").strip(), birth_year, death_year)
        else:
            return list()
    if int(level) <= int(prev_lvl):
        return people
    else:
        while int(level) == int(prev_lvl) + 1:
            prev_pers.add_child(cur_pers)
            remaining = parse_familyBranch(people[1::], level, cur_pers)
            if remaining:
                (_, level, name, birth_year, death_year, id_number, _) = remaining[0]
                cur_pers = Person(name, id_number.replace(" ", "").strip(), birth_year, death_year)
                if int(level) == int(prev_lvl) + 1:
                    people = remaining
                    continue
                else:
                    return remaining
            else:
                return list()

def parse_family_tree(f):
    """
    turns the txt version of the family tree into a csv file for use in OpenRefine
    :param f: a txt file containing the OCR'ed family tree
    """
    tree = (re.split(tree_entry, f))
    with open("familyTree.csv", "w+", encoding="UTF-8") as ft:
        ft.write("Name ; ID ; Birth ; Birth Place ; Death ; Place of Death\n")
        i = 1
        for line in tree[1::]:
            if line == "":
                ft.write("\n")
                i = 1
            else:
                if i in [1, 2, 5]:
                    ft.write(line + " ; ")
                elif i == 3:
                    if line.split()[0] == "b:":
                        ft.write(line + " ; ")
                    else:
                        ft.write(" ;  ;" + line + " ; ")
                        i = 6
                elif i == 4:
                    if line.split()[0] == "d:":
                        ft.write(" ; " + line + " ; ")
                        i = 6
                    else:
                        ft.write(line + " ; ")
                elif i == 6:
                    ft.write(line)
                i += 1
            if i == 7:
                i = 1


def update_family_tree(progenitor):
    """
    update the tree beneath progenitor based on a csv exported from open-refine.
    """
    with open("OpenRefineData.csv", "r", encoding="UTF-8") as f:
        data = f.read().split("\n")[1::]
        data = list(map(lambda s: s.split(","),data))
        update_person(progenitor, data)
        return progenitor


def update_person(person, data):
    """
    helper function for "update_family_tree" which recursively updates a person in the tree and their spouse/children
    :return:
    """
    ids = list(map(lambda x: x[0], data))
    if person.id_number in ids:
        i = ids.index(person.id_number)
        updates = data[i]
        if updates[4]:
            person.add_gender(updates[4])
        if updates[5]:
            person.add_birth_date(updates[5])
        if updates[7]:
            person.add_birth_place(updates[7], updates[8], updates[9], updates[10])
        if updates[11]:
            person.add_death_date(updates[11])
        if updates[13]:
            person.add_death_place(updates[13], updates[14], updates[15], updates[16])
        if updates[18]:
            person.add_burial_place(updates[18], updates[19], updates[20], updates[21])
    else:
        print(person.id_number + " not found in openrefine data")
    if person.spouse:
        update_person(person.spouse, data)
    for child in person.children:
        update_person(child, data)


def tree_to_gedcom(person):
    """
    convert the family tree beneath person from a python object to GEDCOM format
    """
    with open("familyTree.ged", "w+", encoding="UTF-8") as ged:
        ged.write("""
0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
1 SOUR GS
2 NAME Waldinger Family Tree
2 VERS 5.5.5
1 DATE 9 June 2020
1 LANG English""")
        person_to_gedcom(ged, person, "10")
        family_to_gedcom(ged, person)
        ged.write("""
0 TRLR""")


def person_to_gedcom(ged, person, family_id):
    """
    responsible for turning the information about an individual in the tree into GEDCOM format
    """
    ged.write("""
0 @I""" + (person.id_number if "B" not in person.id_number else person.id_number[0:-1] + "99999") + """@ INDI
1 NAME """ + person.given_name + " /" + person.surname + """/
2 SURN """ + person.surname + """
2 GIVN """ + person.given_name)

    if person.gender:
        ged.write("""
1 SEX """ + person.gender[0].upper())

    if person.birth_date:
        ged.write("""
1 BIRT
2 DATE """ + person.birth_date)

    if person.birth_place and person.birth_date:
        ged.write("""
2 PLAC """ + person.birth_place.name)

        if person.birth_place.lat and person.birth_place.long and person.birth_place.wiki_data_id:
            ged.write("""
3 MAP
4 LATI """ + person.birth_place.lat + """
4 LONG """ + person.birth_place.long + """
3 NOTE https://www.wikidata.org/wiki/""" + person.birth_place.wiki_data_id)

    elif person.birth_place:
        ged.write("""
1 BIRT
2 PLAC """ + person.birth_place.name)

        if person.birth_place.lat and person.birth_place.long and person.birth_place.wiki_data_id:
            ged.write("""
3 MAP
4 LATI """ + person.birth_place.lat + """
4 LONG """ + person.birth_place.long + """
3 NOTE https://www.wikidata.org/wiki/""" + person.birth_place.wiki_data_id)

    if person.death_date:
        ged.write("""
1 DEAT
2 DATE """ + person.death_date)

    if person.death_place and person.death_date:
        ged.write("""
2 PLAC """ + person.death_place.name)

        if person.death_place.lat and person.death_place.long and person.death_place.wiki_data_id:
            ged.write("""
3 MAP
4 LATI """ + person.death_place.lat + """
4 LONG """ + person.death_place.long + """
3 NOTE https://www.wikidata.org/wiki/""" + person.death_place.wiki_data_id)

    elif person.death_place:
        ged.write("""
1 DEAT
2 PLAC """ + person.death_place.name)

        if person.death_place.lat and person.death_place.long and person.death_place.wiki_data_id:
            ged.write("""
3 MAP
4 LATI """ + person.death_place.lat + """
4 LONG """ + person.death_place.long + """
3 NOTE https://www.wikidata.org/wiki/""" + person.death_place.wiki_data_id)

    if person.burial_place:
        ged.write("""
1 BURI
2 PLAC """ + person.burial_place.name)

        if person.burial_place.lat and person.burial_place.long and person.burial_place.wiki_data_id:
            ged.write("""
3 MAP
4 LATI """ + person.burial_place.lat + """
4 LONG """ + person.burial_place.long + """
3 NOTE https://www.wikidata.org/wiki/""" + person.burial_place.wiki_data_id)

    if person.id_number not in ["10"] and person.id_number[-1] != "B":
        ged.write("""
1 FAMC @F""" + family_id + "@")

    if person.spouse or person.children:
        ged.write("""
1 FAMS @F""" + person.id_number + """@""")

        if person.spouse:
            person_to_gedcom(ged, person.spouse, person.id_number)
            ged.write("""
1 FAMS @F""" + person.id_number + "@")

        for child in person.children:
            person_to_gedcom(ged, child, person.id_number)


def family_to_gedcom(ged, person):
    """
    responsible for turning the information about a family in the tree into GEDCOM format, essentially determining
    the connections between the different individuals.
    """
    ged.write("""
0 @F""" + person.id_number + """@ FAM
1 """ + ("HUSB" if person.gender == "male" else "WIFE") + " @I" + person.id_number + "@")

    if person.spouse:
        ged.write("""
1 """ + ("HUSB" if person.spouse.gender == "male" else "WIFE") + " @I" + person.spouse.id_number[0:-1] + "99999" + "@")

    for child in person.children:
        ged.write("""
1 """ + "CHIL" + " @I" + child.id_number + "@")

    for child in person.children:
        family_to_gedcom(ged, child)



parse()

