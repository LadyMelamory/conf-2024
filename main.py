import re
import shutil
import time
from pprint import pprint

import pandas as pd


# interlay_options = [u'тонкое', u'неравномерное', u'в основном тонкое']

# дефолтная зернистость - МЗ
class GRIT_TYPES:
    THIN = u'тонкозернистый'  # 1  # тонкозернистый
    SMALL = u'мелкозернистый'  # 2  # мелкозернистый
    MEDIUM = u'среднезернистый'  # 3  # среднезернистый
    BIG = u'крупнозернистый'  # 4  # крупнозернистый
    DIFFERENT = u'разнозернистый'  # 5  # разнозернистый


class ROCK_TYPES:
    SANDSTONE = u'песчаник'  # 1  # песчаник
    ARGILLITE = u'аргиллит'  # 2  # аргиллит
    SILTSTONE = u'алевролит'  # 3  # алевролит
    COAL = u'уголь'  # 4  # уголь
    LIMESTONE = u'известняк'  # 5  # известняк
    GRITSTONE = u'конгломерат'  # 6  # гравелит, конгломерат


class TEXTURE_TYPES:
    MASSIVE = u'массивная'  # 1 # массивная
    HORIZONTAL_LAYERING = u'горизонтальная слоистость'  # 2 # горизонтальная слоистость
    FLAT_WAVY_LAYERING = u'пологоволнистая слоистость'  # 3 # пологоволнистая слоистость
    LENTICULAR_WAVY_LAYERING = u'линзовидноволнистая слоистость'  # 4 # линзовидноволнистая слоистость
    OBLIQUE_WAVY_LAYERING = u'косоволнистая слоистость'  # 5 # косоволнистая слоистость
    OBLIQUE_LAYERING = u'косая слоистость'  # 6 # косая слоистость
    SCHISTOSITY = u'слоеватость'  # 7 # слоеватость
    RHYTHMIC_OCCURRENCE = u'ритмит'  # 8 # ритмит


class AMOUNT:
    ABUNDANCE_OF_DIFFERENT_FORMS = u'обилие разных форм'  # 1 #
    SIGNIFICANT = u'значительное'  # 1 #
    AVERAGE = u'среднее'  # 1 #
    SMALL = u'небольшое'  # 1 #
    ABSENCE = u'отсутствие'  # 1 #


class DEFORMATION_TYPES:
    BIOTURBATION = u'биотурбация'
    TURBULENCE = u'взмучивания'
    SLIDDS = u'оползания'


class OTHER:
    PYRITE = u'пирит'
    BELEMNITES = u'белемниты'
    # SLIDDS = u'оползания'


# TODO: песчаный материал не в песчанике
rock_patterns = [
    {'type': ROCK_TYPES.SANDSTONE, 'infinitive': r'песчаник(и?)', 'genetive': r'песчаник(а|ов)',
     'sub_forms': r'песчаник(у|ом|ам|ами)'},
    {'type': ROCK_TYPES.ARGILLITE, 'infinitive': r'аргиллит(ы?)|глин(а|ы)', 'genetive': r'аргиллит(а|ов)|глин(ы?)\b',
     'sub_forms': r'аргиллит(у|ом|ам|ами)'},
    {'type': ROCK_TYPES.SILTSTONE, 'infinitive': r'алевролит(ы?)', 'genetive': r'алевролит(а|ов)',
     'sub_forms': r'алевролит(у|ом|ам|ами)'},
    {'type': ROCK_TYPES.COAL, 'infinitive': r'уголь|угли\b', 'genetive': r'угл(я|ей)', 'sub_forms': r'угл(ё|е)м'},
    {'type': ROCK_TYPES.LIMESTONE, 'infinitive': r'известняк(и?)', 'genetive': r'известняк(а|ов)',
     'sub_forms': r'известняк(у|ом|ам|ами)'},
    {'type': ROCK_TYPES.GRITSTONE, 'infinitive': r'гравелит(ы?)|конгломерат(ы?)',
     'genetive': r'гравелит(а|ов)|конгломерат(а|ов)', 'sub_forms': r'гравелит(у|ом|ам|ами)|конгломерат(у|ом|ам|ами)'},
]

oil_sign_patterns = [r'нефтенасыщенн\w+', r'(?<!без )(признаков )*нефтенасыщения(?! нет)', r'(?<!без )нефтенасыще\w+',
                     r'(?<!отсутствие )(признаков )*нефтенасыщения', r'признаки ув']

grit_patterns = [
    {'grit_type': GRIT_TYPES.THIN,
     'pattern': r'/bтз/b|т/з|тонкозернис|мелко-тонкозернис|тонко-мелкозернист'},
    {'grit_type': GRIT_TYPES.SMALL,
     'pattern': r'/bмз/b|м/з|мелкозернис|мелко-тонкозернис|тонко-мелкозернист|мелко-крупнозернист'},
    {'grit_type': GRIT_TYPES.MEDIUM, 'pattern': r'/bсз/b|с/з|среднезернис|мелко-среднезернис|средне-мелкозернист'},
    {'grit_type': GRIT_TYPES.BIG, 'pattern': r'/bкз/b|к/з|крупнозернис|средне-крупнозернис|мелко-крупнозернист'},
    {'grit_type': GRIT_TYPES.DIFFERENT, 'pattern': r'разнозернис'},
]

# TODO: контакт четкий, пологоволнистый
texture_patterns = [
    {'texture_type': TEXTURE_TYPES.MASSIVE, 'pattern': r'массивн', 'col': 18},
    {'texture_type': TEXTURE_TYPES.HORIZONTAL_LAYERING, 'pattern': r'горизонтальн', 'col': 19},
    {'texture_type': TEXTURE_TYPES.FLAT_WAVY_LAYERING,
     'pattern': r'пологоволнист|линзовидно-пологоволнист|(?<!-)волнист', 'col': 20},
    {'texture_type': TEXTURE_TYPES.LENTICULAR_WAVY_LAYERING, 'pattern': r'линзовидн', 'col': 21},
    {'texture_type': TEXTURE_TYPES.OBLIQUE_WAVY_LAYERING, 'pattern': r'косоволнист', 'col': 22},
    {'texture_type': TEXTURE_TYPES.OBLIQUE_LAYERING, 'pattern': r'кос(ая|ую)', 'col': 23},
    {'texture_type': TEXTURE_TYPES.SCHISTOSITY, 'pattern': r'слоеватость', 'col': 24},
    {'texture_type': TEXTURE_TYPES.RHYTHMIC_OCCURRENCE, 'pattern': r'ритмит', 'col': 25},
]

grit_rock_cols = [
    {'grit_type': None, 'rock_type': ROCK_TYPES.LIMESTONE, 'col': 6},
    {'grit_type': None, 'rock_type': ROCK_TYPES.COAL, 'col': 7},
    {'grit_type': None, 'rock_type': ROCK_TYPES.ARGILLITE, 'col': 8},
    {'grit_type': GRIT_TYPES.SMALL, 'rock_type': ROCK_TYPES.SILTSTONE, 'col': 9},
    {'grit_type': GRIT_TYPES.BIG, 'rock_type': ROCK_TYPES.SILTSTONE, 'col': 10},
    {'grit_type': GRIT_TYPES.DIFFERENT, 'rock_type': ROCK_TYPES.SILTSTONE, 'col': 11},
    {'grit_type': GRIT_TYPES.THIN, 'rock_type': ROCK_TYPES.SANDSTONE, 'col': 12},
    {'grit_type': GRIT_TYPES.SMALL, 'rock_type': ROCK_TYPES.SANDSTONE, 'col': 13},
    {'grit_type': GRIT_TYPES.MEDIUM, 'rock_type': ROCK_TYPES.SANDSTONE, 'col': 14},
    {'grit_type': GRIT_TYPES.BIG, 'rock_type': ROCK_TYPES.SANDSTONE, 'col': 15},
    {'grit_type': GRIT_TYPES.DIFFERENT, 'rock_type': ROCK_TYPES.SANDSTONE, 'col': 16},
    {'grit_type': None, 'rock_type': ROCK_TYPES.GRITSTONE, 'col': 17},
]

plant_patterns = [
    {'pattern': r'следы листьев', 'col': 31},  # поискать паттерны
    {'pattern': r'\bкорн', 'col': 32},
    {'pattern': r'обломки древесины', 'col': 33},  # поискать паттерны
    {'pattern': r'крупн(ый|ого) детрит(а?)', 'col': 34},
    {'pattern': r'детрит|\bУРД\b', 'col': 35},
    {'pattern': r'\bсечк', 'col': 36},
    {'pattern': r'аттрит(а?)', 'col': 37},
]

deformation_patterns = [
    {'type': DEFORMATION_TYPES.BIOTURBATION,
     'pattern': r'биотурбац|\bСЖРО\b|(след(ы|ов) жизнедеятельности|ход(ы|ов)) роющих организмов'},
    {'type': DEFORMATION_TYPES.TURBULENCE, 'pattern': r'взмучивани'},
    {'type': DEFORMATION_TYPES.SLIDDS, 'pattern': r'оползани'},  #
]

other_patterns = [
    {'pattern': r'обломк(?!и древесины)', 'col': 38},  # не древесина
    {'pattern': r'сидерит', 'col': 40},  #
    {'pattern': r'УГМ|УСМ|углисто(-?)глинист|углисто(-?)слюдист', 'col': 41},  #
    {'pattern': r'карбонат', 'col': 42},  # надо именно цемент?
]

note_patterns = [
    {'type': OTHER.PYRITE, 'pattern': r'пирит'},
    {'type': OTHER.BELEMNITES, 'pattern': r'белемнит'},
    # {'type': OTHER, 'pattern': r'оползани'},  #
]

col_names = {'№ скважины': 0, u'Пласт НИК УВЗУ': 1, u'Порядковый номер слоя': 3, u'Толщина, м': 4}
OUTPUT_FIRST_ROW = 5

df = pd.read_excel(u'D:/Projects/conf-2024/data/Исходник.xlsx', header=6)
result_df = pd.DataFrame(columns=range(45), index=[0])


def find_grit(rock, desc=None):
    for grit_pattern in grit_patterns:
        if re.search(grit_pattern['pattern'], rock['desc'] if desc is None else desc, flags=re.I):
            rock['grit'].add(grit_pattern['grit_type'])


def split_rocks(sent):
    rocks = []
    for rock_pattern in rock_patterns:
        for rock_m in re.finditer(r'' + f"({rock_pattern['infinitive']}|{rock_pattern['genetive']}|"
                                        f"{rock_pattern['sub_forms']})(?! составляет)", sent, flags=re.I):
            rocks.append({'type': rock_pattern['type'], 'start': rock_m.start(), 'grit': set()})
    # pprint(rocks)
    rocks.sort(key=lambda r: r['start'])
    length = len(rocks)
    for i in range(length):
        start = 0 if i == 0 else rocks[i]['start']
        end = None if length < 2 or i == length - 1 else rocks[i + 1]['start']
        # print(rocks[i]['type'], sent[start:end])
        rocks[i]['desc'] = sent[start:end]
    return rocks


def save_grit(grit_type, row, sign):
    cols = [x['col'] for x in grit_rock_cols if
            (x["grit_type"] in rock['grit'] or x["grit_type"] is None) and x["rock_type"] == grit_type]
    if cols:
        for col in cols:
            if row not in result_df.index or pd.isna(result_df.at[row, col]) or result_df.at[row, col] == u'НЕТУ':
                result_df.at[row, col] = sign
        return
    if not cols and grit_type == ROCK_TYPES.SANDSTONE:
        if row in result_df.index and pd.isna(result_df.at[row, 13]):
            result_df.at[row, 13] = u'НЕТУ'
    if not cols and grit_type == ROCK_TYPES.SILTSTONE:
        if row in result_df.index and pd.isna(result_df.at[row, 9]):
            result_df.at[row, 9] = u'НЕТУ'


for i in range(df.shape[0]):
    full_desc = df[u'Послойное описание'][i]  # возможно называется не так
    rock_names = df[u'Порода'][i]  # возможно называется не так
    sentences = full_desc.split('.')
    main_rocks = set()
    sub_rocks = set()
    found_rocks = {'+': [], '-': []}
    if not pd.isna(rock_names):
        for rock_pattern in rock_patterns:
            if re.search(r'' + f"{rock_pattern['infinitive']}", rock_names, flags=re.I):
                main_rocks.add(rock_pattern['type'])
            if re.search(r'(?<!слойками )' + f"{rock_pattern['genetive']}", rock_names, flags=re.I):
                main_rocks.add(rock_pattern['type'])
    print(full_desc)

    oil_saturated = False
    for sent in sentences:
        # print(rock)
        # поиск признаков УВ
        for oil_sign in oil_sign_patterns:
            if bool(re.search(oil_sign, sent, flags=re.I)):
                oil_saturated = True
                break
        sent_rocks = split_rocks(sent)
        for current_rock in sent_rocks:
            # если породу видим в первый раз и она есть в главных - тогда плюс, иначе минус - перепроверить
            # поделить предложение на части и искать зернистость только в области породы
            curr_type = current_rock['type']
            if curr_type not in main_rocks:
                if curr_type in [ROCK_TYPES.SANDSTONE, ROCK_TYPES.SILTSTONE]:
                    find_grit(current_rock)
                found_rocks['-'].append(current_rock)
                sub_rocks.add(current_rock['type'])
            else:
                main = next((x for x in found_rocks['+'] if x["type"] == current_rock['type']), None)
                if main is None:
                    # первый раз встречаем породу
                    if curr_type in [ROCK_TYPES.SANDSTONE, ROCK_TYPES.SILTSTONE]:
                        find_grit(current_rock)
                    found_rocks['+'].append(current_rock)
                elif curr_type in [ROCK_TYPES.SANDSTONE, ROCK_TYPES.SILTSTONE]:
                    if not main['grit']:
                        find_grit(main, current_rock['desc'])
                    else:
                        find_grit(current_rock)
                        found_rocks['-'].append(current_rock)
                        sub_rocks.add(curr_type)
    print(main_rocks, sub_rocks)
    # print('+') nnn
    # pprint(found_rocks['+'], sort_dicts=False)
    # plus = ''
    for rock in found_rocks['+']:
        # plus += '\n'.join([rock['type'], ', '.join(rock['grit'])]) + '\n'
        save_grit(rock['type'], i, '+')
        pass
        # plus += '\n'.join([rock['desc'],  rock['type'], ', '.join(rock['grit'])])
        # print(rock['desc'], '\n', rock['type'], ', '.join(rock['grit']))

    if pd.isna(rock_names):
        result_df.at[i, 43] = u'НЕТ ИМЕНИ'
    # print('-')
    # minus = ''
    for rock in found_rocks['-']:
        # minus += '\n'.join([rock['type'], ', '.join(rock['grit'])]) + '\n'
        save_grit(rock['type'], i, '-')
        # print(rock['desc'], '\n', rock['type'], ', '.join(rock['grit']))

    for texture_pattern in texture_patterns:
        if re.search(texture_pattern['pattern'], full_desc, flags=re.I):
            result_df.at[i, texture_pattern['col']] = '+'

    for plant_pattern in plant_patterns:
        if re.search(plant_pattern['pattern'], full_desc, flags=re.I):
            result_df.at[i, plant_pattern['col']] = '+'

    for deformation_pattern in deformation_patterns:
        if re.search(deformation_pattern['pattern'], full_desc, flags=re.I):
            result_df.at[i, 39] = ((result_df.at[i, 39] + ', ' if i in result_df.index and not pd.isna(
                result_df.at[i, 39]) else '')
                                   + deformation_pattern['type'])

    for other_pattern in other_patterns:
        if re.search(other_pattern['pattern'], full_desc, flags=re.I):
            result_df.at[i, other_pattern['col']] = '+'

    for note_pattern in note_patterns:
        if re.search(note_pattern['pattern'], full_desc, flags=re.I):
            result_df.at[i, 43] = ((result_df.at[i, 43] + ', ' if i in result_df.index and not pd.isna(
                result_df.at[i, 43]) else '')
                                   + note_pattern['type'])

    # pprint(found_rocks['-'], sort_dicts=False)

    for col_n in col_names:
        result_df.at[i, col_names[col_n]] = df[col_n][i]
    result_df.at[i, 2] = str(df[u'Верх интервала долбления, м'][i]) + '-' + str(df[u'Низ интервала долбления, м'][i])
    if oil_saturated:
        result_df.at[i, 5] = '+'
    result_df.at[i, 44] = full_desc
    # result_df.at[i, 4] = rock_names

# with pd.ExcelWriter('output.xlsx', engine="xlsxwriter") as writer:
#     writer.book.formats[0].set_text_wrap()
#     df.to_excel(writer, startrow=1, sheet_name='row_1_to_3')

filename = u'data/Результат_' + time.strftime("%Y%m%d-%H%M%S") + '.xlsx'
shutil.copy("data/Шаблон.xlsx", filename)
with pd.ExcelWriter(filename, engine='openpyxl', mode="a", if_sheet_exists='overlay') as writer:
    # writer.book.formats[0].set_text_wrap()
    result_df.to_excel(writer, startrow=OUTPUT_FIRST_ROW, startcol=1, sheet_name=u'Лист1', index=False, header=False)
