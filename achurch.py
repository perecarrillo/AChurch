from __future__ import annotations
from dataclasses import dataclass


from antlr4 import *
from lcLexer import lcLexer
from lcParser import lcParser
from lcVisitor import lcVisitor
import re
import pydot

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


@dataclass
class Lletra:
    x: chr


@dataclass
class Aplicacio:
    esq: Terme
    dre: Terme


@dataclass
class Abstraccio:
    x: chr
    dre: Terme

Terme = Lletra | Aplicacio | Abstraccio


@dataclass
class TreeVisitor(lcVisitor):
    def visitParentesis(self, ctx):
        [par1, terme, par2] = list(ctx.getChildren())
        return self.visit(terme)

    def visitAplicacio(self, ctx):
        [e, d] = list(ctx.getChildren())
        return Aplicacio(self.visit(e), self.visit(d))

    def visitAbstraccio(self, ctx):
        [lam, x, punt, dre] = list(ctx.getChildren())
        x = x.getText()
        r = self.visit(dre)
        while len(x) != 1:
            r = Abstraccio(x[-1], r)
            x = x[:-1]
        return Abstraccio(x, r)

    def visitLletra(self, ctx):
        [x] = list(ctx.getChildren())
        return Lletra(x.getText())

    def visitGroot(self, ctx):
        [t] = list(ctx.getChildren())
        return self.visit(t)

    def visitMacroDefinicio(self, ctx):
        [macro, ig, terme] = list(ctx.getChildren())
        macros[macro.getText()] = self.visit(terme)
        return -1

    def visitMacro(self, ctx):
        [m] = list(ctx.getChildren())
        return macros[m.getText()]

    def visitInmacro(self, ctx):
        [t1, m, t2] = list(ctx.getChildren())
        return Aplicacio(Aplicacio(macros[m.getText()], self.visit(t1)), self.visit(t2))


@dataclass
class Avaluador(lcVisitor):

    def avalua(self, t):
        t1 = self.avaluaUn(t)
        while escriu(t) != escriu(t1):
            t1, t = self.avaluaUn(t1), t1
        return t1

    def avaluaUn(self, t):
        match t:
            case Aplicacio(l, r):
                match l:
                    case Abstraccio(a, b):
                        b = self.buscaAlfaConversio(r, b)
                        # print("β-reducció:")
                        res = self.betaReduccio(a, r, b)
                        # print(escriu(Aplicacio(Abstraccio(a, b), r)), " → ", escriu(res))
                        global msg
                        msg.append(escriu(Aplicacio(Abstraccio(a, b), r)) + " → β → " + escriu(res))
                        return res
                    case _:
                        # Pq sigui ordre normal, si el de la esq te alguna transformacio el de la dreta no sha devaluar
                        return Aplicacio(self.avaluaUn(l), self.avaluaUn(r))
            case Abstraccio(l, r):
                return Abstraccio(l, self.avaluaUn(r))
            case Lletra(c):
                return t

    def betaReduccio(self, x: chr, sub: Terme, rest: Terme) -> Terme:
        match rest:
            case Lletra(c):
                if c == x:
                    return sub
                else:
                    return rest
            case Aplicacio(l, r):
                return Aplicacio(self.betaReduccio(x, sub, l), self.betaReduccio(x, sub, r))
            case Abstraccio(l, r):
                return Abstraccio(l, self.betaReduccio(x, sub, r))

    # volem buscar i substituir sub a busca
    def buscaAlfaConversio(self, sub: Terme, busca: Terme) -> Terme:
        result = busca
        lSubTotals = self.agafaLletres(sub, False)
        lSubLligades = self.agafaLletres(sub, True)
        lSub = lSubTotals ^ lSubLligades
        lBuscaAbs = self.agafaLletres(busca, True)        # On buscar
        lBuscaTotal = self.agafaLletres(busca, False)    # Totes les lletres
        inter = lBuscaAbs.intersection(lSub)
        for l in inter:
            novaLletra = self.getNovaLletra(lSub.union(lBuscaTotal))
            # print(f"α-conversió: {l} → {novaLletra}")
            # print(escriu(result), " →   ", end="")
            m = escriu(result) + " → α → "
            lBuscaTotal.update(novaLletra)
            result = self.alfaConversio(l, novaLletra, result)
            # print(escriu(result))
            m += escriu(result)
            global msg
            msg.append(m)

        return result

    def alfaConversio(self, ant: chr, nou: chr, rest: Terme) -> Terme:
        match rest:
            case Lletra(c):
                if c == ant:
                    return Lletra(nou)
                return Lletra(c)
            case Aplicacio(l, r):
                return Aplicacio(self.alfaConversio(ant, nou, l), self.alfaConversio(ant, nou, r))
            case Abstraccio(c, r):
                if c == ant:
                    return Abstraccio(nou, self.alfaConversio(ant, nou, r))
                return Abstraccio(c, self.alfaConversio(ant, nou, r))

    Alfabet = {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'}

    def getNovaLletra(self, unusable: set(chr)):
        return (self.Alfabet ^ unusable).pop()

    #                         cert si busquem nomes lletres al costat duna lambda
    def agafaLletres(self, t, b: bool) -> set(chr):
        match t:
            case Lletra(c):
                if b:
                    return set()
                return {c}
            case Aplicacio(l, r):
                res = self.agafaLletres(l, b).union(self.agafaLletres(r, b))
                return res
            case Abstraccio(c, r):
                res = set(c).union(self.agafaLletres(r, b))
                return res


def escriu(a: Terme) -> str:
    match a:
        case Lletra(x):
            return x

        case Aplicacio(esq, dre):
            return "(" + escriu(esq) + escriu(dre) + ")"

        case Abstraccio(x, dre):
            return "(λ" + x + "." + escriu(dre) + ")"


def seg():
    i = 0
    while True:
        yield str(i)
        i += 1


def creaGraf(tree):
    graph = pydot.Dot("abs", graph_type="graph")
    # Afegim un numero diferent al final de l'identificador de cada node per que no coincideixin mai
    num = seg()

    def crea(t, lligades):
        match t:
            case Lletra(x):
                node = pydot.Node(x+next(num), label=x, color="white")
                graph.add_node(node)
                if x in lligades.keys():
                    graph.add_edge(pydot.Edge(node, lligades[x], dir="forward", style="dotted"))
                return node
            case Aplicacio(esq, dre):
                node = pydot.Node("@"+next(num), label="@", color="white")
                graph.add_node(node)
                esq = crea(esq, lligades)
                dre = crea(dre, lligades)
                graph.add_edge(pydot.Edge(node, esq, dir="forward"))
                graph.add_edge(pydot.Edge(node, dre, dir="forward"))
                return node
            case Abstraccio(x, dre):
                node = pydot.Node(f"λ{x}{next(num)}", label=f"λ{x}", color="white")
                graph.add_node(node)
                lligades[x] = node
                dre = crea(dre, lligades)
                graph.add_edge(pydot.Edge(node, dre, dir="forward"))
                return node
    crea(tree, {})
    return graph

macros = {}
msg = []

# For console interpreter
# while True:
#     input_stream = InputStream(input('? '))
#     lexer = AChurchLexer(input_stream)
#     token_stream = CommonTokenStream(lexer)
#     parser = AChurchParser(token_stream)
#     tree = parser.root()
#     visitor = TreeVisitor()
#     t = visitor.visit(tree)
#     if t == -1:
#         for k, v in macros.items():
#             print(f"{k} ≡ {escriu(v)}")
#     else:
#         print("Arbre:")
#         print(escriu(t))

#         avaluador = Avaluador()
#         res = avaluador.avalua(t)
#         print("Resultat:")
#         print(escriu(res))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        "AChurchBot!\n\n"
        f"Benvingut {user.first_name}!  👋\n\n")
    # return 0

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "AChurchBot!\n\n"
        "/start  👶🏻\n"
        "/author  👤\n"
        "/help  🤔\n"
        "/macros  🧬\n"
        "Expressió λ-càlcul  💬")

async def author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "AChurchBot!\n\n"
        "Pere Carrillo, 2023")

async def mcrs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mac = ""
    for key, val in macros.items():
        mac += f"{key} ≡ {escriu(val)} \n"
    if mac == "":
        await update.message.reply_text("Encara no has definit cap macro 💔")
    else:
        await update.message.reply_text(mac)

async def eval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input = update.message.text
    input_stream = InputStream(input)
    lexer = lcLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = lcParser(token_stream)
    tree = parser.root()
    visitor = TreeVisitor()
    t = visitor.visit(tree)
    if t != -1:
        global msg
        msg = []
        await update.message.reply_text(escriu(t))
        graph = creaGraf(t)
        await context.bot.send_photo(update.message.chat_id, graph.create_png())
        avaluador = Avaluador()
        res = avaluador.avalua(t)
        msg.append(escriu(res))
        for m in msg:
            await update.message.reply_text(m)
        graph = creaGraf(res)
        await context.bot.send_photo(update.message.chat_id, graph.create_png())
    else:
        await update.message.reply_text(f"La macro {re.split('=|≡', input)[0]} s'ha definit correctament 🎁")


def main() -> None:
    """Run the bot."""

    tokenFile = open("token.txt", "r+")
    token = tokenFile.read()
    # print(token)
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)

    author_handler = CommandHandler('author', author)
    application.add_handler(author_handler)

    macros_handler = CommandHandler('macros', mcrs)
    application.add_handler(macros_handler)

    message = MessageHandler(None, eval)
    application.add_handler(message)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":

    main()
