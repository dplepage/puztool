class StuffList:
    def __init__(self, rows, typ):
        self.rows = [typ(*row) for row in rows]
        self.typ = typ
        self.fields = self.typ._fields

    def __contains__(self, term):
        return bool(self.get(term))

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, term):
        return self.one(term)

    def get(self, term):
        items = [i for i in self.rows if term in i]
        return items

    def first(self, term):
        items = self.get(term)
        if items:
            return items[0]
        return None

    def one(self, term):
        items = self.get(term)
        l = len(items)
        if l != 1:
            raise ValueError(
                f"Expected exactly one match for {term}, got {len(items)}")
        return items[0]

    def col(self, name):
        return [getattr(x,name) for x in self.rows]
