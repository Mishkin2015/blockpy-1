from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from block import Block
from block.chain import Blockchain
from json_api import APIHandler


app = APIHandler()

class NodeServerHandler():

    @app.when_get('/blocks')
    def list_blocks(self, params=None):
        chain = self.server.chain
        return 200, {'items': [item.to_dict() for item in chain]}

    @app.when_get('/blocks/last')
    def get_last_block(self, params=None):
        chain = self.server.chain
        last = chain.last()
        if last is None:
            return 404, {'error': 'blockchain is empty'}
        else:
            return 200, last.to_dict()

    @app.when_post('/blocks')
    def insert_block(self, data):
        try:
            new_block = Block(data.get('index'), data.get('previous_hash'), data.get('data'))
            self.server.chain.append(new_block)
            result_report = {"ok": True, "hash": new_block.hash}
            result_code = 200
        except Exception as error:
            result_report = {'error': error.message}
            result_code = 500
        return result_code, result_report


class Node(HTTPServer):

    def __init__(self, port=8181):
        self.port = port
        self.chain = Blockchain()
        server_address = ('', port)
        super().__init__(server_address, app.serve)

    def serve(self):
        try:
            self.serve_forever()
        finally:
            self.server_close()

    @classmethod
    def run(cls, port=8181, handler_class=NodeServerHandler):
        return cls(port=port).serve()


if __name__ == '__main__':
    Node.run()
