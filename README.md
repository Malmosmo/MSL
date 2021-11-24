# MinecraftScriptingLanguage
A programming language that compiles to minecraft commands.

# Install
```
pip install git+https://github.com/Malmosmo/MSL.git
```

# Example
```
//> main

for (i = 0; i < 5; i++) {
  as ("@e[distance=..2]"), at ("@s") {
    say hello there
  }
}

```
compiles to
```
#> main
execute as @e[distance=..2] at @s run say hello there
execute as @e[distance=..2] at @s run say hello there
execute as @e[distance=..2] at @s run say hello there
execute as @e[distance=..2] at @s run say hello there
execute as @e[distance=..2] at @s run say hello there
```
