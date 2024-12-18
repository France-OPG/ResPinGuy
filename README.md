# ResPinGuy - The Kompiler
## Créer une image ISO de son système Linux.

⚠!!! ResPinGuy ne fonctionne pas encore !!!⚠

![ResPinGuy](https://respinguy.fopg.fr/logo-img-theme/logo/ResPinGuy-BF.png)

### Dépendance :
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


### Simple utilisateur :
Install Command:

Install with sudo :
```bash
wget respinguy.fopg.fr/ftp/file/rpg-ins && sudo bash rpg-ins
```
Install with su (root) :
```bash
wget respinguy.fopg.fr/ftp/file/rpg-ins && bash rpg-ins
```

### Forkeur :
Fork Command:
```bash
git clone https://github.com/ResPinGuy/ResPinGuy.git
```

### Documentation
[Documentation](https://github.com/France-OPG/ResPinGuy/blob/main/documentation.md)


&copy; 2023 [ResPinGuy](https://respinguy.fopg.fr/)
