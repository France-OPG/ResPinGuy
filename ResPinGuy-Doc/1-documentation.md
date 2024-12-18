# ResPinGuy - The Kompiler
## Créer une image ISO de son système Linux.
## Documentation Officiel

### Rappel des dépendances :
- git
- wget
- sudo
- bash
- sh
- nano
- uname (avec prise en charge de -r et -m)
- mksquashfs (avec prise en charge de -comp xz, la dépendance est généralement appelée: squashfs-tools)
- dracut (avec prise en charge des modules squash et dmsquash-live)
- xorriso


### (Version sudo) Liste des commandes avec leurs fonction :

Liste des commandes avec leurs fonction :
```bash
sudo respinguy
```
Modifier la configuration :
```bash
sudo respinguy-config
```
Lancer la création d'une image ISO :
```bash
sudo respinguy-build
```
Mettre a jour respinguy :
```bash
sudo respinguy-app-up
```
Vérifier les dépendances :
```bash
sudo respinguy-app-dep
```
Supprimer respinguy :
```bash
sudo respinguy-app-rm
```

### (Version root) Liste des commandes avec leurs fonction :

Liste des commandes avec leurs fonction :
```bash
respinguy
```
Modifier la configuration :
```bash
respinguy-config
```
Lancer la création d'une image ISO :
```bash
respinguy-build
```
Mettre a jour respinguy :
```bash
respinguy-app-up
```
Vérifier les dépendances :
```bash
respinguy-app-dep
```
Supprimer respinguy :
```bash
respinguy-app-rm
```

&copy; 2023 [ResPinGuy](https://respinguy.tk)