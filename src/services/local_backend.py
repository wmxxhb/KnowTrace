import ast
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from src.settings import settings
from src.models.vector import SearchResult


def connect(vector_store=False):
    path = settings.BASE_DIR / 'data' / 'local-services.db'
    if vector_store:
        model = settings.EMBEDDING_MODEL.replace('/', '_')
        path = settings.VECTOR_DIR / f'{model}-{settings.MILVUS_DIMENSION}.db'
    db = sqlite3.connect(path, timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, kb_id INTEGER, vector TEXT, metadata TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS memory (session TEXT, message TEXT, created REAL)')
    return db


class LocalVectorClient:
    def insert(self, records):
        with connect(vector_store=True) as db:
            db.executemany('INSERT OR REPLACE INTO vectors VALUES (?, ?, ?, ?)', [
                (r.id, int(r.metadata.get('kb_id', 0)), json.dumps(r.values), json.dumps(r.metadata)) for r in records])

    def search(self, vector, top_k=10, expr=None):
        sql, args = 'SELECT id, vector, metadata FROM vectors', []
        if expr:
            if expr.startswith('kb_id in '):
                args = ast.literal_eval(expr[len('kb_id in '):])
                sql += ' WHERE kb_id IN (' + ','.join('?' for _ in args) + ')'
            elif expr.startswith('kb_id == '):
                sql += ' WHERE kb_id = ?'
                args = [int(expr[len('kb_id == '):])]
            else:
                raise ValueError('Unsupported vector filter')
        with connect(vector_store=True) as db:
            rows = db.execute(sql, args).fetchall()
        results = []
        for record_id, values, metadata in rows:
            values, metadata = json.loads(values), json.loads(metadata)
            if len(values) != len(vector):
                raise ValueError('Embedding dimensions do not match')
            results.append(SearchResult(id=record_id, score=sum((a-b)**2 for a,b in zip(values, vector)), text=metadata.get('text', ''), metadata=metadata))
        return sorted(results, key=lambda r: r.score)[:top_k]


class LocalMemory:
    def lrange(self, key, start, end):
        with connect() as db:
            return [r[0] for r in db.execute('SELECT message FROM memory WHERE session=? AND created>? ORDER BY rowid DESC LIMIT ? OFFSET ?', (key, time.time()-settings.SHORT_TERM_MEMORY_TTL, end-start+1, start))]

    def lpush(self, key, message):
        with connect() as db:
            db.execute('INSERT INTO memory VALUES (?, ?, ?)', (key, message, time.time()))
            db.execute('DELETE FROM memory WHERE session=? AND rowid NOT IN (SELECT rowid FROM memory WHERE session=? ORDER BY rowid DESC LIMIT ?)', (key, key, settings.MEMORY_HISTORY_LIMIT))

    def ltrim(self, key, start, end):
        pass  # History is trimmed atomically in lpush.

    def expire(self, key, ttl):
        pass  # Reads apply the configured TTL.

    def delete(self, key):
        with connect() as db:
            db.execute('DELETE FROM memory WHERE session=?', (key,))


class LocalStream:
    def __init__(self, path):
        self.file = path.open('rb')

    def stream(self, size):
        while chunk := self.file.read(size):
            yield chunk

    def close(self):
        self.file.close()

    def release_conn(self):
        pass


class LocalStorage:
    def __init__(self):
        self.root = (settings.BASE_DIR / 'data' / 'objects').resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name):
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError('Invalid object name')
        return path

    def upload_file(self, object_name, file_data, content_type='application/octet-stream'):
        path = self.path(object_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_data)
        return True

    def list_files(self, prefix='', sort_by='last_modified', order='desc', search_query=''):
        files = []
        for path in self.root.rglob('*'):
            if path.is_file():
                name = path.relative_to(self.root).as_posix()
                if name.startswith(prefix) and search_query.lower() in name.lower():
                    stat = path.stat()
                    files.append(dict(object_name=name, size=stat.st_size, last_modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc), etag=''))
        key = sort_by if sort_by in ('last_modified', 'size') else 'object_name'
        return sorted(files, key=lambda item: item[key], reverse=order=='desc')

    def get_file_stream(self, object_name):
        path = self.path(object_name)
        return LocalStream(path) if path.is_file() else None

    def get_file_url(self, object_name):
        raise ValueError('Local files use the authenticated download button')

    def delete_file(self, object_name):
        self.path(object_name).unlink(missing_ok=True)
        return True

    def batch_delete_files(self, object_names):
        for name in object_names:
            self.delete_file(name)
        return True
