#!/usr/bin/env python

__author__ = "Florian Hase"

# =======================================================================

import time

# =======================================================================


class AddEntry(object):
    def __init__(self, database, table, entry):
        self.db = database
        self.table = table
        self.entry = entry

    def execute(self):
        with self.db.connect() as conn:
            conn.execute(self.table.insert(), self.entry)


# =======================================================================


class FetchEntries(object):
    def __init__(self, database, table, selection):
        self.db = database
        self.table = table
        self.selection = selection
        self.entries = None
        self.executed = False
        self.entries_fetched = False

    def execute(self):
        with self.db.connect() as conn:
            selected = conn.execute(self.selection)
            entries = selected.fetchall()
        self.entries = entries
        self.executed = True

    def get_entries(self):
        while not self.executed:
            time.sleep(0.02)
        self.entries_fetched = True
        return self.entries


# =======================================================================


class UpdateEntries(object):
    def __init__(self, database, table, updates):
        self.db = database
        self.table = table
        self.updates = updates

    def execute(self):
        with self.db.connect() as conn:
            conn.execute(self.updates)
