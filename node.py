from http.server import HTTPServer
from block import Block
from block.chain import Blockchain
from api.serve import APIHandler
from api.client import APIClient
from collections import deque


app = APIHandler()


class NodeServerHandler():

    @app.when_get('/blocks')
    def list_blocks(self, params=None):
        chain = self.server.chain
        index_start = 0
        if isinstance(params, dict):
            index_start_values = params.get('from_index')
            if type(index_start_values) == list:
                index_start = int(index_start_values[0])
        items = [item.to_dict() for item in chain if item.index >= index_start]
        return 200, {'items': items}

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
        result_code = 200
        result_report = {'result', 'unkown'}
        try:
            new_block = Block(data.get('index'), data.get('previous_hash'), data.get('data'))
            self.server.add_block(new_block, report=data.get('new', False))
            result_report = {"ok": True, "hash": new_block.hash}
        except Exception as error:
            result_report = {'error': error.message}
            result_code = 500
        return result_code, result_report

    @app.when_post('/peers')
    def add_peer(self, data):
        new_host = data.get('peer')
        if new_host not in [peer.host for peer in self.server.peers]:
            self.server.new_peer(new_host)
            return 201, {'ok': True}
        return 200, {'ok': True, 'known': True}


class NodeClient(APIClient):

    def __init__(self, host):
        self.errors = deque()
        super().__init__(host)

    def update_with_data(self, response, current):
        for data in response.get('items', []):
            try:
                index = data.get('index')
                new_block = Block(index, data.get('previous_hash'), data.get('data'))
                current.append(new_block)
            except Exception as error:
                self.errors.append(error)

    def update(self, current):
        status_code, result = 200, None
        try:
            processed_index = max([block.index for block in current])
            index_param = {'from_index': processed_index + 1}
            status_code, result = self.get(url='/blocks', params=index_param)
            self.update_with_data(result, current)
        except Exception as error:
            self.errors.append(error)
            status_code, result = 500, {'error': str(error)}
        return status_code, result

    def report(self, new_block):
        try:
            return self.post(url='/blocks', data=new_block.to_dict())
        except Exception as error:
            self.errors.append(error)
            return 500, {'error': str(error)}


class Node(HTTPServer):
    allow_reuse_address = True

    def __init__(self, port=8181, genesis_block=None, peers=[]):
        self.set_chain(genesis_block)
        self.listen(port)
        self.set_peers(peers)
        self.update_from_peers()

    def set_chain(self, genesis_block):
        self.chain = Blockchain()
        if genesis_block is not None:
            self.chain.append(genesis_block)

    def add_block(self, new_block, report=False):
        self.chain.append(new_block)
        if report is True:
            self.report_to_peers(new_block)

    def listen(self, port):
        server_address = ('', port)
        super().__init__(server_address, app.serve)

    def set_peers(self, peers):
        self.peers = []
        for peer in peers:
            self.new_peer(peer)

    def new_peer(self, host):
        new_node = NodeClient(host)
        self.peers.append(new_node)
        new_node.update(self.chain)

    def serve(self):
        try:
            self.serve_forever()
        finally:
            self.server_close()

    def update_from_peers(self):
        for peer in self.peers:
            peer.update(self.chain)

    def report_to_peers(self, new_block):
        for peer in self.peers:
            peer.report(new_block)

    @classmethod
    def run(cls, port=8181):
        return cls(port=port).serve()


if __name__ == '__main__':
    Node.run()
