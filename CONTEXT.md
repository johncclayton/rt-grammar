# RealTest scripts

This context is the language of a RealTest `.rts` Script as we talk about it, with Lark rule names as the tree alias so programs can walk [realtest.lark](realtest.lark) without a third vocabulary.

Speech is RealTest-first (item, section, parameter, element, setting). The one deliberate exception: we say **Expression** for any Item’s right-hand side; RealTest errors still say “formula.”

## Script structure

**Script**:
A RealTest `.rts` file.
Lark: `start`
_Avoid_: document, module, file

**Section**:
A container of Items, such as Data or Strategy. A Strategy section may carry a Name; a Data section does not.
Lark: `*_section`
_Avoid_: header, block, stanza

**Item**:
Any `Name: value` line. `RSIV:`, `NumPositions:`, `Side:`, and `AccountSize:` are all Items.
_Avoid_: statement, declaration, assignment

## Item families

**Named item**:
An Item whose left-hand Name the author chose.
Lark: `ITEM_LABEL`
_Avoid_: user item, identifier, variable

**Keyword**:
An Item whose left-hand word is reserved.
Lark: `*_KW`
_Avoid_: reserved item, key

**Name**:
The spoken word for both creating and using (`RSIV`). The colon is punctuation, not a spoken concept. In an Expression, `RSI`, `C`, `RSIV`, and `RSIPeriod` are all Names.
Lark: `NAME` (after stripping the colon from `ITEM_LABEL` / `*_KW`)
_Avoid_: label, identifier, variable, symbol, built-in

## Named-item kinds

**Data item**:
A named item in Data, TestData, or StratData.
Lark: `data_item_decl`

**Library item**:
A named item in Library; an inline shortcut, not a stored series.
Lark: `library_decl`

**Parameter**:
A named item in Parameters.
Lark: `param_decl`

**Column**:
A named item in Scan, TestScan, Trades, Results, Graphs, or Charts.
Lark: `column_decl`

## Keyword kinds

**Setting**:
A keyword in Settings* or Import, including `BarSize` and `DataValueFile` when they appear inside Data.
Lark: `set_*_decl`, `imp_*_decl`, `data_barsize_decl`, `data_valuefile_decl`

**Element**:
A keyword in Strategy, Template, Benchmark, StatsGroup, or Combined.
Lark: `str_*_decl`, `grp_*_decl`
_Avoid_: strategy item

**Filter**:
The Filter keyword in scan-like sections.
Lark: `filter_decl`

**Sort**:
The Sort keyword in scan-like sections.
Lark: `sort_decl`

## Expressions

**Expression**:
Any Item’s right-hand side: `RSI(RSIPeriod)`, `#Fill RSI(RSIPeriod)`, `Long`, `100000`, or `from 2 to 5 step 1 def 2`.
Lark: `tagged_value` / `expr`, `LINE_VALUE`, enum terminals, `signed_number`, parameter range, …
_Avoid_: value, formula (except when quoting a RealTest error)

**Function call**:
An Expression of the form `RSI(RSIPeriod)`.
Lark: `funcall`

**Function**:
The Name being called (`RSI`).
Lark: `NAME` in `funcall`

**Argument**:
One slot inside a Function call. `RSIPeriod` in `RSI(RSIPeriod)` is an Argument; the Parameters-section Item named RSIPeriod is a Parameter.
Lark: `argument`
_Avoid_: parameter (for the slot), input, operand

**Literal**:
A number or string in an Expression (`50`, `"n-day"`).
Lark: `NUMBER`, `STRING`
_Avoid_: constant, scalar

## Not spoken

These exist in the tree or in RealTest errors. Do not use them in speech.

**Label** — left-hand token with the colon. Lark: `ITEM_LABEL`, `*_KW`

**Header** — section-opening token. Lark: `*_HDR`

**Tag** — `#Fill` and other `#` prefixes; they are part of the Expression. Lark: `hash_tag`

**Formula** — RealTest’s word (and Lark `expr`) for a computed Expression

**Value** — older word for Expression
