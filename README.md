# tcgclinter - a linter for TCG Collector card resource files

This is a tool I use while writing card resource files for tcgcollector.com to
try and prevent basic mistakes I make over and over.

I don't expect this to be particularly useful to anyone, but here it is anyway.

## Example

```
$ poetry run tcgclinter -rv ../cards/vcb-random-constructed-starter-decks/
Processing 26 source card files.
Checking set Japan > PCG Era > Venusaur, Charizard & Blastoise Random Constructed Starter Decks (531)
| Checking card Bulbasaur 001/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Bulbasaur 002/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Ivysaur 003/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Venusaur ex 004/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Paras 005/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Parasect 006/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Venonat 007/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Venomoth 008/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Charmander 009/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Charmander 010/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Charmeleon 011/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Charizard ex 012/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Growlithe 013/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Arcanine 014/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Ponyta 015/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Rapidash 016/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
Warning: (Rapidash 016/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)) wrong attacks sorting order: [1, 1]
| Checking card Squirtle 017/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Squirtle 018/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Wartortle 019/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Blastoise ex 020/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Shellder 021/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Cloyster 022/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Krabby 023/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Kingler 024/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Magnemite 025/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
| Checking card Magneton 026/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)
Error:   (Magneton 026/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)) Evolution Pokémon is missing evolvesFrom
| Checking set consistency

Summary
Warning: (Rapidash 016/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)) wrong attacks sorting order: [1, 1]
Error:   (Magneton 026/052 (Japan / Venusaur, Charizard & Blastoise Random Constructed Starter Decks)) Evolution Pokémon is missing evolvesFrom

Found 1 errors and 1 warnings.
```
