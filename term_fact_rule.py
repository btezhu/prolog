from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, List


class TermType(Enum):
	Var = "variable"
	Rule = "rule"
	Atom = "atom"

	def __str__(self) -> str:
		return self._value_

class Term:
	all_terms: 'dict[TermType, dict[str, Term]]' = {type: {} for type in TermType}

	def __init__(self, name: str, type: TermType):
		self.name = name
		self.type = type

		for term_type in self.all_terms:
			assert name not in self.all_terms[term_type], f"This name is already used by the {term_type} '{name}'"

		self.all_terms[self.type][name] = self

	@staticmethod
	def _term(name: str, type: TermType) -> 'Term':
		for term_name in Term.all_terms[type]:
			if name == term_name: return Term.all_terms[type][name]
		return Term(name, type)

	@staticmethod
	def atom(name: str) -> 'Term':
		assert name[0].islower(), name
		return Term._term(name, TermType.Atom)
	
	@staticmethod
	def variable(name: str) -> 'Term':
		assert name[0].isupper()
		return Term._term(name, TermType.Var)
	
	@staticmethod
	def rule(name: str) -> 'Term':
		assert name[0].islower(), "A rule cannot be capitalised!"
		return Term._term(name, TermType.Rule)
	
	def __call__(self, *args: 'Term') -> 'Fact':
		assert self.type == TermType.Rule, f"Cannot call a {self.type}!"
		return Fact(self, list(args))
	
	def __repr__(self) -> str:
		return self.name
	
	def __eq__(self, value) -> bool:
		if not isinstance(value, Term): return False
		return self.name == value.name
	
	@staticmethod
	def print_all():
		for type in Term.all_terms:
			print(f"{type}:")
			[print(term) for term in Term.all_terms[type]]
			print()

class ExprType(Enum):
	And = "and"
	Or = "or"

	def op(self) -> str:
		match self:
			case self.And: return ','
			case self.Or: return ';'
			case _:
				assert False, f"Not implemented: {self._name_}"

@dataclass
class Expr(ABC):
	arg1: 'ExprOrFact'
	arg2: 'ExprOrFact'
	type: ExprType
	is_variable: bool = field(init=False, default=False)

	def __post_init__(self):
		for arg in [self.arg1, self.arg2]:
			if arg.is_variable: self.is_variable = True

	@staticmethod
	def And(*args: 'ExprOrFact') -> 'ExprOrFact':
		left, *arguments = args
		while arguments: left = Expr(left, arguments.pop(0), ExprType.And)
		return left
	
	@staticmethod
	def Or(*args: 'ExprOrFact') -> 'ExprOrFact':
		left, *arguments = args
		while arguments: left = Expr(left, arguments.pop(0), ExprType.Or)
		return left

	def __repr__(self) -> str:
		return f"({self.arg1}{self.type.op()} {self.arg2})"
	
	def replace(self, var_dict: dict[str, Term]) -> 'Expr':
		return Expr(self.arg1.replace(var_dict), self.arg2.replace(var_dict), self.type)
	
	def get_variables(self) -> set[str]:
		return self.arg1.get_variables() | self.arg2.get_variables()
	
	def __and__(self, other: 'ExprOrFact') -> 'ExprOrFact':
		return And(self, other)
	
	def __or__(self, other: 'ExprOrFact') -> 'ExprOrFact':
		return Or(self, other)

@dataclass
class Rule:
	fact: 'Fact'
	body: 'ExprOrFact'
	adding: ClassVar[bool] = False

	all_rules: 'ClassVar[List[Rule]]' = []

	def __post_init__(self):
		assert self.fact.is_variable
		assert self.body.is_variable
		if self.adding: self.all_rules.append(self)

	@classmethod
	def print_all(cls):
		[print(rule) for rule in cls.all_rules]

	def __repr__(self) -> str:
		return f"{self.fact} :- {self.body}"

@dataclass
class Fact:
	adding: ClassVar[bool] = False
	rule: Term
	arguments: List[Term]
	is_variable: bool = field(init=False, default=False)

	all_facts: 'ClassVar[List[Fact]]' = []

	def __post_init__(self):
		assert self.rule.type == TermType.Rule
		for argument in self.arguments:
			assert argument.type == TermType.Var or argument.type == TermType.Atom
			if argument.type == TermType.Var: self.is_variable = True
		if self.adding and not self.is_variable:
			self.all_facts.append(self)

	def __repr__(self) -> str:
		return f"{self.rule}({', '.join(map(str, self.arguments))})"
	
	def replace(self, var_dict: dict[str, Term]) -> 'Fact':
		return Fact(self.rule, [var_dict.get(term.name, term) if term.type == TermType.Var else term for term in self.arguments])
		assert False, self

	def get_variables(self) -> set[str]:
		return {term.name for term in self.arguments if term.type == TermType.Var}
	
	def __eq__(self, value) -> bool:
		if not isinstance(value, Fact): return False
		return self.rule == value.rule and len(self.arguments) == len(value.arguments) and all([self_arg == other_arg for (self_arg, other_arg) in zip(self.arguments, value.arguments)])
	
	def __and__(self, other: 'ExprOrFact') -> 'ExprOrFact':
		return And(self, other)
	
	def __or__(self, other: 'ExprOrFact') -> 'ExprOrFact':
		return Or(self, other)
	
	@classmethod
	def print_all(cls):
		[print(fact) for fact in cls.all_facts]
		
class AddingFacts:
	def __enter__(self):
		self.old_adding = Fact.adding
		Fact.adding = True
	
	def __exit__(self, *_):
		Fact.adding = self.old_adding

class AddingRules:
	def __enter__(self):
		self.old_adding = Rule.adding
		Rule.adding = True
	
	def __exit__(self, *_):
		Rule.adding = self.old_adding

def add_facts(*facts: Fact):
	# print("facts", facts)
	for fact in facts:
		if fact not in Fact.all_facts:
			Fact.all_facts.append(fact)

def add_rules(*rules: Rule):
	for rule in rules:
		if rule not in Rule.all_rules:
			Rule.all_rules.append(rule)

ExprOrFact = Expr | Fact
And = Expr.And
Or = Expr.Or