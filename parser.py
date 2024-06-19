from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from term_fact_rule import And, ExprOrFact, Fact, Or, Rule, Term

@dataclass
class Location:
	col: int = 0 
	line: int = 0

class TokenType(Enum):
	IDENT = "ident"
	LPAREN = "lparen"
	RPAREN = "rparen"
	PERIOD = "period"
	EOF = "eof"
	COMMA = "comma"
	COLONDASH = "colon-dash"
	SEMICOLON = "semicolon"

	@staticmethod
	def from_char(c: str) -> 'TokenType':
		match c:
			case '(': return TokenType.LPAREN
			case ')': return TokenType.RPAREN
			case '.': return TokenType.PERIOD
			case ',': return TokenType.COMMA
			case ';': return TokenType.SEMICOLON
			case _: assert False, c

	def __repr__(self) -> str:
		return self._value_
	
	def __str__(self) -> str:
		return repr(self)
	
@dataclass
class Token:
	source: str
	type: TokenType
	location: Location

	def __repr__(self) -> str:
		return f"{self.type}('{self.source}')"

class Lexer:
	def __init__(self, source: str):
		self.source = source
		self.position = 0
		self.location: Location = Location(self.position, 0)
		self.peeked: Optional[Token] = None

	@staticmethod
	def from_file(file_path: str) -> 'Lexer':
		with open(file_path, 'r') as f:
			return Lexer(f.read())
		
	def advance(self) -> str:
		# TODO: Actually advance the location
		self.position += 1
		return self.source[self.position] if self.position < len(self.source) else ''

	def next_token(self) -> Token:
		if self.peeked is not None:
			token, self.peeked = self.peeked, None
			return token
		
		while self.position < len(self.source) and self.source[self.position].isspace(): self.advance()
		if self.position >= len(self.source): return Token('\0', TokenType.EOF, self.location)

		match self.source[self.position]:
			case c if c.isalpha() or c == '_':
				start = self.position
				start_location = self.location
				while self.position < len(self.source) and (self.source[self.position].isalpha() or self.source[self.position] == '_'): self.advance()
				ident = self.source[start:self.position]
				return Token(ident, TokenType.IDENT, start_location)
			case c if c in '().,;': 
				location = self.location
				self.advance()
				return Token(c, TokenType.from_char(c), location)
			case ':' if self.position < len(self.source)-1 and self.source[self.position+1] == '-':
				location = self.location
				self.advance()
				self.advance()
				return Token(':-', TokenType.COLONDASH, location)
			case c: assert False, f"Unimplemented: '{c}'"

	def peek_token(self) -> Token:
		if self.peeked is not None: return self.peeked
		self.peeked = self.next_token()
		return self.peeked

	def check_token(self, *token_types: TokenType) -> bool:
		return self.peek_token().type in token_types
	
	def expect(self, *token_types: TokenType) -> Token:
		token = self.next_token()
		assert token.type in token_types, f"Expected {list(token_types)}, but got {token.type}"
		return token
	
	def take_token(self, *token_types: TokenType) -> Optional[Token]:
		if self.check_token(*token_types):
			return self.expect(*token_types)
		return None
	
def parse_atom_or_variable(lexer: Lexer) -> Term:
	name = lexer.expect(TokenType.IDENT).source
	if name[0].isupper():
		return Term.variable(name)
	else:
		return Term.atom(name)

def parse_fact(lexer: Lexer) -> Fact:
	name = lexer.expect(TokenType.IDENT)
	lexer.expect(TokenType.LPAREN)
	arguments: list[Term] = []
	if not lexer.check_token(TokenType.RPAREN):
		arguments.append(parse_atom_or_variable(lexer))
		while lexer.take_token(TokenType.COMMA):
			arguments.append(parse_atom_or_variable(lexer))
	lexer.expect(TokenType.RPAREN)
	# TODO: Don't create the Term if parsing in a query
	# assert name.source in Term.all_terms[TermType.Rule], f"existence_error: {name.source}"
	return Fact(Term.rule(name.source), arguments)

def parse_primary(lexer: Lexer) -> ExprOrFact:
	if lexer.take_token(TokenType.LPAREN):
		fact_or_expr = parse_fact_or_expr(lexer)
		lexer.expect(TokenType.RPAREN)
		return fact_or_expr
	
	return parse_fact(lexer)

precedences: list[dict[TokenType, Callable[[ExprOrFact, ExprOrFact], ExprOrFact]]] = [
	{TokenType.COMMA: And},
	{TokenType.SEMICOLON: Or}
]

def parse_expression_at_level(lexer: Lexer, level: int) -> ExprOrFact:
	if level >= len(precedences): return parse_primary(lexer)
	left = parse_expression_at_level(lexer, level+1)
	while (token := lexer.take_token(*list(precedences[level]))):
		left = precedences[level][token.type](left, parse_expression_at_level(lexer, level+1))
	return left

def parse_fact_or_expr(lexer: Lexer) -> ExprOrFact:
	return parse_expression_at_level(lexer, 0)

def parse_statement(lexer: Lexer) -> Fact | Rule:
	fact = parse_fact(lexer)
	if lexer.take_token(TokenType.COLONDASH):
		return Rule(fact, parse_fact_or_expr(lexer))
	lexer.expect(TokenType.PERIOD)
	lexer.expect(TokenType.EOF)
	assert not fact.is_variable, f"Unimplemented: variable facts/bodyless rules"
	return fact

def parse_query(lexer: Lexer) -> ExprOrFact:
	fact_or_expr = parse_fact_or_expr(lexer)
	lexer.expect(TokenType.PERIOD)
	lexer.expect(TokenType.EOF)
	return fact_or_expr