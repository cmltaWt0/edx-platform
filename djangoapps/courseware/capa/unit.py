import math
import operator

from numpy import eye, array

from pyparsing import Word, alphas, nums, oneOf, Literal
from pyparsing import ZeroOrMore, OneOrMore, StringStart
from pyparsing import StringEnd, Optional, Forward
from pyparsing import CaselessLiteral, Group, StringEnd
from pyparsing import NoMatch, stringEnd

base_units = ['meter', 'gram', 'second', 'ampere', 'kelvin', 'mole', 'cd']
unit_vectors = dict([(base_units[i], eye(len(base_units))[:,i]) for i in range(len(base_units))])


def unit_evaluator(unit_string, units=unit_map):
    ''' Evaluate an expression. Variables are passed as a dictionary
    from string to value. Unary functions are passed as a dictionary
    from string to function '''
    if string.strip() == "":
        return float('nan')
    ops = { "^" : operator.pow,
            "*" : operator.mul,
            "/" : operator.truediv,
            }
    prefixes={'%':0.01,'k':1e3,'M':1e6,'G':1e9,
              'T':1e12,#'P':1e15,'E':1e18,'Z':1e21,'Y':1e24,
              'c':1e-2,'m':1e-3,'u':1e-6,
              'n':1e-9,'p':1e-12}#,'f':1e-15,'a':1e-18,'z':1e-21,'y':1e-24}
    
    def super_float(text):
        ''' Like float, but with si extensions. 1k goes to 1000'''
        if text[-1] in suffixes:
            return float(text[:-1])*suffixes[text[-1]]
        else:
            return float(text)

    def number_parse_action(x): # [ '7' ] ->  [ 7 ]
        return [super_float("".join(x))]
    def exp_parse_action(x): # [ 2 ^ 3 ^ 2 ] -> 512
        x = [e for e in x if type(e) == float] # Ignore ^
        x.reverse()
        x=reduce(lambda a,b:b**a, x)
        return x
    def parallel(x): # Parallel resistors [ 1 2 ] => 2/3
        if len(x) == 1:
            return x[0]
        if 0 in x:
            return float('nan')
        x = [1./e for e in x if type(e) == float] # Ignore ^
        return 1./sum(x)
    def sum_parse_action(x): # [ 1 + 2 - 3 ] -> 0
        total = 0.0
        op = ops['+']
        for e in x:
            if e in set('+-'):
                op = ops[e]
            else:
                total=op(total, e)
        return total
    def prod_parse_action(x): # [ 1 * 2 / 3 ] => 0.66
        prod = 1.0
        op = ops['*']
        for e in x:
            if e in set('*/'):
                op = ops[e]
            else:
                prod=op(prod, e)
        return prod
    def func_parse_action(x):
        return [functions[x[0]](x[1])]

    number_suffix=reduce(lambda a,b:a|b, map(Literal,suffixes.keys()), NoMatch()) # SI suffixes and percent
    (dot,minus,plus,times,div,lpar,rpar,exp)=map(Literal,".-+*/()^")
    
    number_part=Word(nums)
    inner_number = ( number_part+Optional("."+number_part) ) | ("."+number_part) # 0.33 or 7 or .34
    number=Optional(minus | plus)+ inner_number + \
        Optional(CaselessLiteral("E")+Optional("-")+number_part)+ \
        Optional(number_suffix) # 0.33k or -17
    number=number.setParseAction( number_parse_action ) # Convert to number
    
    # Predefine recursive variables
    expr = Forward() 
    factor = Forward()
    
    def sreduce(f, l):
        ''' Same as reduce, but handle len 1 and len 0 lists sensibly '''
        if len(l)==0:
            return NoMatch()
        if len(l)==1:
            return l[0]
        return reduce(f, l)

    # Handle variables passed in. E.g. if we have {'R':0.5}, we make the substitution. 
    # Special case for no variables because of how we understand PyParsing is put together
    if len(variables)>0:
        varnames = sreduce(lambda x,y:x|y, map(lambda x: CaselessLiteral(x), variables.keys()))
        varnames.setParseAction(lambda x:map(lambda y:variables[y], x))
    else:
        varnames=NoMatch()
    # Same thing for functions. 
    if len(functions)>0:
        funcnames = sreduce(lambda x,y:x|y, map(lambda x: CaselessLiteral(x), functions.keys()))
        function = funcnames+lpar.suppress()+expr+rpar.suppress()
        function.setParseAction(func_parse_action)
    else:
        function = NoMatch()

    atom = number | varnames | lpar+expr+rpar | function
    factor << (atom + ZeroOrMore(exp+atom)).setParseAction(exp_parse_action) # 7^6
    paritem = factor + ZeroOrMore(Literal('||')+factor) # 5k || 4k
    paritem=paritem.setParseAction(parallel)
    term = paritem + ZeroOrMore((times|div)+paritem) # 7 * 5 / 4 - 3
    term = term.setParseAction(prod_parse_action)
    expr << Optional((plus|minus)) + term + ZeroOrMore((plus|minus)+term) # -5 + 4 - 3
    expr=expr.setParseAction(sum_parse_action)
    return (expr+stringEnd).parseString(string)[0]

if __name__=='__main__':
    variables={'R1':2.0, 'R3':4.0}
    functions={'sin':math.sin, 'cos':math.cos}
    print "X",evaluator(variables, functions, "10000||sin(7+5)-6k")
    print "X",evaluator(variables, functions, "13")
    print evaluator({'R1': 2.0, 'R3':4.0}, {}, "13")
    # 
    print evaluator({'a': 2.2997471478310274, 'k': 9, 'm': 8, 'x': 0.66009498411213041}, {}, "5")
    print evaluator({},{}, "-1")
    print evaluator({},{}, "-(7+5)")
    print evaluator({},{}, "-0.33")
    print evaluator({},{}, "-.33")
    print evaluator({},{}, "5+7 QWSEKO")
