
from itertools import product
import sys
from typing import Optional

from parser import Lexer, parse_statement, parse_query
from term_fact_rule import Expr, ExprOrFact, ExprType, Fact, Rule, Term, TermType, add_facts, add_rules

debug = False

def matches(pattern: list[Term], terms: list[Term]) -> Optional[dict[str, Term]]:
	var_dict: dict[str, Term] = {}
	if len(pattern) != len(terms): return None
	for (pattern_term, term) in zip(pattern, terms):
		assert pattern_term.name not in var_dict, f"Not implemented: proper pattern matching, {pattern}"
		var_dict[pattern_term.name] = term
	return var_dict

def query_simple(fact: ExprOrFact, depth:int=0) -> bool:
	if debug: print(f"{chr(9)*depth}Querying simple... {fact}")
	assert not fact.is_variable, "Cannot do a simple query on a variable expression"
	if isinstance(fact, Fact):
		for rule in Rule.all_rules:
			if rule.fact.rule == fact.rule:
				vars_dict = matches(rule.fact.arguments, fact.arguments)
				if vars_dict is None: continue
				if query(rule.body.replace(vars_dict), depth+1, False): return True
		return fact in Fact.all_facts
	elif isinstance(fact, Expr):
		match fact.type:
			case ExprType.And: return query_simple(fact.arg1, depth+1) and query_simple(fact.arg2, depth+1)
			case ExprType.Or: return query_simple(fact.arg1, depth+1) or query_simple(fact.arg2, depth+1)
			case _: assert False, f"Unimplemented: {fact.type}"
	else:
		assert False, f"Unimplemented: {fact}"

def query_variable(fact: ExprOrFact, depth:int=0, needs_all_answers: bool=True) -> list[dict[str, Term]]:
	if debug: print(f"{chr(9)*depth}Querying variable... {fact}")
	assert fact.is_variable, "Cannot do a variable query on a simple expression"
	all_var_dicts: list[dict[str, Term]] = []
	variables = fact.get_variables()
	for atoms in product(Term.all_terms[TermType.Atom], repeat=len(variables)):
		var_dict = {var: Term.all_terms[TermType.Atom][atoms[i]] for (i, var) in enumerate(variables)}
		if query_simple(fact.replace(var_dict), depth+1):
			all_var_dicts.append(var_dict)
			if not needs_all_answers: break
	return all_var_dicts

def query(fact: ExprOrFact, depth: int=0, needs_all_var_answers:bool=True) -> bool | list[dict[str, Term]]:
	if fact.is_variable:
		return query_variable(fact, depth, needs_all_var_answers)
	else:
		return query_simple(fact, depth)
	
def print_query(result: bool | list[dict[str, Term]]):
	if isinstance(result, bool): print({True: "yes", False: "no"}[result])
	elif isinstance(result, list):
		if not result:
			print("no")
		for var_dict in result:
			[print(f"{var} = {var_dict[var]}") for var in var_dict]
			print()
	else: assert False, result
	
# TODO: Proper error reporting for syntax/runtime errors
def handle_query(query_str: str):
	query_str, *_ = query_str.strip().split("%")
	if not query_str: return
	lexer = Lexer(query_str)
	fact_or_expr = parse_query(lexer)
	print_query(query(fact_or_expr))

def handle_statement(statement: str):
	statement, *_ = statement.strip().split("%")
	if not statement: return
	lexer = Lexer(statement)
	fact_or_rule = parse_statement(lexer)

	if isinstance(fact_or_rule, Fact): add_facts(fact_or_rule)
	elif isinstance(fact_or_rule, Rule): add_rules(fact_or_rule)
	else: assert False, f"Unimplemented: {fact_or_rule}"

def load_file(path: str):
	with open(path, 'r') as f:
		for line in f.readlines():
			handle_statement(line)

def handle_command(command: list[str]):
	match command:
		case ['q']: exit(0)
		case ['l', path]: load_file(path)
		case ['rules']: Rule.print_all()
		case ['terms']: Term.print_all()
		case ['facts']: Fact.print_all()
		case _: assert False, f"Unknown command: {command}"

COMMAND_PREFIX = ':'

def handle_repl(repl_input: str):
	"""
	Handle a REPL command/query.

	Returns True if the REPL needs to be exited.
	"""
	if not repl_input: return
	if repl_input.startswith(COMMAND_PREFIX): 
		handle_command(repl_input.removeprefix(COMMAND_PREFIX).split())
	else:
		handle_query(repl_input)

def main(files_to_load: list[str]):
	for path in files_to_load:
		load_file(path)
	while True:
		command = input("?- ")
		if command.startswith(COMMAND_PREFIX):
			if handle_command(command.removeprefix(COMMAND_PREFIX).split()): break
		else:
			handle_query(command)

if __name__ == '__main__': main(sys.argv[1:])
