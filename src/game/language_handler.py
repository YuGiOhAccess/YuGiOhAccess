import gettext
import logging
import sqlite3

from pathlib import Path

from core import variables
from core.exceptions import LanguageException

logger = logging.getLogger(__name__)

class LanguageHandler:
    languages = dict()
    primary_language = ''

    def __init__(self):
        self.strings_path = Path(Path(variables.LOCAL_DATA_DIR) / "locales")
        self.card_database_dir = Path(Path(variables.APP_DATA_DIR) / "sync" / "databases2" / "content")

    def add(self, lang, short):
        lang = lang.lower()
        short = short.lower()
        logger.info("Adding language "+lang+" with shortage "+short)
        try:
            language_information = {'short': short}
            language_information['strings'] = self.__parse_strings(short)
            self.languages[lang] = language_information
        except LanguageException as e:
            logger.error("Failed to add language "+lang+": "+str(e))

    def connect_all_databases(self):
        for lang in self.languages.keys():
            logger.info("Connecting database for language "+lang)
            self.languages[lang]['db'] = self.__connect_database()

    def __connect_database(self):
        card_database_file = Path(self.card_database_dir / "cards.cdb")
        if not card_database_file.exists():
            raise LanguageException("cards.cdb not found in "+str(card_database_file.parent))
        cdb = sqlite3.connect(":memory:", check_same_thread=False)
        cdb.row_factory = sqlite3.Row
        cdb.create_function('UPPERCASE', 1, lambda s: s.upper())
        cdb.execute("ATTACH ? AS new", (str(card_database_file), ))
        cdb.execute("CREATE TABLE datas AS SELECT * FROM new.datas WHERE id<100000000")
        cdb.execute("CREATE TABLE texts AS SELECT * FROM new.texts WHERE id<100000000")
        cdb.execute("DETACH new")
        cdb.execute("CREATE UNIQUE INDEX idx_datas_id ON datas (id)")
        cdb.execute("CREATE UNIQUE INDEX idx_texts_id ON texts (id)")

        # getting all column names from cards.cdb
        cursor = cdb.execute("SELECT * FROM datas LIMIT 1")
        row = cursor.fetchone()
        columns = row.keys()
        cursor.close()

        extending_dbs  = Path(self.card_database_dir).glob('*.cdb')
        count = 0
        for p in extending_dbs:
            if p.name == 'cards.cdb':
                continue
            count += 1
            cdb.execute("ATTACH ? as new", (str(p), ))

            # getting all columns currently available in the merged db
            cursor = cdb.execute("SELECT * FROM new.datas LIMIT 1")
            row = cursor.fetchone()
            if not row:
                logger.warning("Database "+str(p)+" is empty")
                cursor.close()
                cdb.execute("DETACH new")
                continue
            new_columns = row.keys()
            cursor.close()

            # getting all columns which are available in both tables
            new_columns = [c for c in new_columns if c in columns]

            cdb.execute("INSERT OR REPLACE INTO datas ({0}) SELECT {0} FROM new.datas WHERE id<100000000".format(', '.join(new_columns)))
            cdb.execute("INSERT OR REPLACE INTO texts SELECT * FROM new.texts WHERE id<100000000")
            cdb.commit()
            cdb.execute("DETACH new")
        logger.info("Merged {count} databases into cards.cdb".format(count = count))
        return cdb

    def __parse_strings(self, language_short):
        strings_file_path = Path(self.strings_path / language_short / "strings.conf")
        if not strings_file_path.exists():
            raise LanguageException(f"strings-{language_short}.conf not found in {strings_file_path.parent}.")
        res = {}
        with open(strings_file_path, 'r', encoding='utf-8') as fp:
            for line in fp:
                line = line.rstrip('\n')
                if not line.startswith('!') or line.startswith('!setcode'):
                    continue
                type, id, s = line[1:].split(' ', 2)
                if id.startswith('0x'):
                    id = int(id, 16)
                else:
                    id = int(id)
                if type not in res:
                    res[type] = {}
                res[type][id] = s.replace('\xa0', ' ')
        return res

    def is_loaded(self, language):
        return language in self.languages

    def set_primary_language(self, lang):
        if not self.is_loaded(lang):
            raise LanguageException("language "+lang+" not loaded and can therefore not be set as primary language")
        self.primary_language = lang

    def get_language(self, lang):
        try:
            return self.languages[lang]
        except KeyError:
            raise LanguageException("language not found")

    def get_strings(self, lang):
        return self.get_language(lang)['strings']

    def get_cards_by_partial_name(self, name):
        name_pattern = f"%{name}%"
        cursor = self.cdb.execute('SELECT id, name FROM texts WHERE name LIKE ?', (name_pattern,))
        rows = cursor.fetchall()
        if not rows:
            return {}
        result = {}
        for row in rows:
            result[row['name']] = row['id']
        return result
    
    def _(self, text):
        language = variables.config.get('language')
        if language == 'english':
            return gettext.NullTranslations().gettext(text)
        else:
            return gettext.translation('game', 'locales', languages=[self.get_language(language)['short']], fallback=True).gettext(text)

    @property
    def primary_database(self):
        return self.get_language(self.primary_language)['db']
    
    @property
    def strings(self):
        return self.get_strings(variables.config.get('language'))
    
    @property
    def cdb(self):
        return self.get_language(variables.config.get("language"))['db']
