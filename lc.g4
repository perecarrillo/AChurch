grammar lc;

root : terme                         #groot
     | (MACRO | INMACRO) ('='|'≡') terme         #macroDefinicio
     ;

terme : terme INMACRO terme           #inmacro
      | MACRO                         #macro
      | '('terme')'                   #parentesis
      | terme terme                   #aplicacio
      | ('λ'|'\\') mes '.' terme      #abstraccio
      | LLETRA                        #lletra
      ;

mes : LLETRA+
      ;

LLETRA : [a-z] ;

MACRO : [A-Z\u0080-\u00FF][0-9A-Z\u0080-\u00FF]*;

INMACRO : ([-/^|$%&#'?¿~·@!"¬] | '+' | '*' | '[' | ']' | '{' | '}' | '\\')+ ;

WS  : [ \t\n\r]+ -> skip ;