import hashlib
import json
from time import time
from app import db
from models import Block
import logging

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.initialized = False
        
    def initialize(self):
        """Initialize blockchain from the database (called after app context is available)"""
        if self.initialized:
            return
            
        try:
            # Check if blockchain exists in DB
            blocks = Block.query.order_by(Block.id).all()
            
            if not blocks:
                # Create the genesis block if blockchain doesn't exist
                self.new_block(previous_hash="1", proof=100)
            else:
                # Load the blockchain from the database
                for block in blocks:
                    self.chain.append({
                        'index': block.id,
                        'timestamp': block.timestamp.timestamp() if hasattr(block.timestamp, 'timestamp') else block.timestamp,
                        'previous_hash': block.previous_hash,
                        'hash': block.hash,
                        'nonce': block.nonce,
                        'data': json.loads(block.data)
                    })
            
            self.initialized = True
            logging.info(f"Blockchain initialized with {len(self.chain)} blocks")
                
        except Exception as e:
            logging.error(f"Error initializing blockchain: {str(e)}")
            # Initialize with empty chain if there's an error
            self.chain = []
            self.current_votes = []

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain
        """
        previous_hash = previous_hash or self.chain[-1]['hash'] if self.chain else "1"
        
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'data': self.current_votes,
            'previous_hash': previous_hash,
            'nonce': proof
        }
        
        # Calculate hash of this block
        block_string = json.dumps(block, sort_keys=True).encode()
        block['hash'] = hashlib.sha256(block_string).hexdigest()
        
        # Reset the current list of votes
        self.current_votes = []
        
        # Add block to chain
        self.chain.append(block)
        
        # Save to database
        # Convert timestamp to datetime for PostgreSQL compatibility
        from datetime import datetime
        new_block = Block(
            timestamp=datetime.fromtimestamp(block['timestamp']),
            previous_hash=block['previous_hash'],
            hash=block['hash'],
            nonce=block['nonce'],
            data=json.dumps(block['data'])
        )
        db.session.add(new_block)
        db.session.commit()
        
        return block

    def new_vote(self, vote_data):
        """
        Creates a new vote to go into the next mined Block
        """
        self.current_votes.append(vote_data)
        
        # If we have enough votes, mine a new block
        if len(self.current_votes) >= 2:  # Arbitrary number, could be adjusted
            last_block = self.last_block
            proof = self.proof_of_work(last_block)
            self.new_block(proof)
            
        # Return the index of the block that will hold this vote
        return self.last_block['index'] + 1 if self.current_votes else self.last_block['index']

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:
        - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
        - p is the previous proof, and p' is the new proof
        """
        last_proof = last_block['nonce']
        last_hash = self.hash(last_block)
        
        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
            
        return proof
    
    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof: Does hash(last_proof, proof, last_hash) contain 4 leading zeroes?
        """
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """
        Returns the last Block in the chain
        """
        return self.chain[-1] if self.chain else {
            'index': 0,
            'timestamp': time(),
            'data': [],
            'previous_hash': "1",
            'nonce': 100,
            'hash': "1"
        }

    def is_valid_chain(self):
        """
        Determine if a given blockchain is valid
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Check that the hash of the block is correct
            if current_block['previous_hash'] != self.hash(previous_block):
                return False
                
            # Check that the Proof of Work is correct
            if not self.valid_proof(previous_block['nonce'], current_block['nonce'], previous_block['hash']):
                return False
                
        return True
