# ResPinGuy
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
- grub-mkstandalone ou grub2-mkstandalone (UEFI, recommandé)
- mkfs.vfat (dosfstools) et mcopy (mtools) pour l'UEFI


### Interface interactive

La commande `respinguy` ouvre un menu plein écran :

```bash
sudo respinguy
```

Actions disponibles :
- Créer l'image ISO (avec un résumé avant lancement)
- Configuration (nom, dossier de sortie, home, kernel, dossiers inclus)
- Paramètres et info : dépendances, mise à jour, suppression, langue, aide

Accès direct à une page :

```bash
sudo respinguy --build
sudo respinguy --config
sudo respinguy --deps
sudo respinguy --help
```

L'interface utilise `whiptail` (ou `dialog`) lorsqu'il est disponible,
sinon un menu texte simple. Aucune dépendance supplémentaire n'est obligatoire.
L'affichage s'adapte automatiquement à la taille de la fenêtre.

Les réglages choisis dans l'interface sont enregistrés dans
`/usr/share/ResPinGuy-File-Config/respinguy-config.local`.
Ce fichier est prioritaire sur `respinguy-config` et peut être supprimé
pour revenir aux valeurs par défaut (menu Configuration > Réinitialiser).


### Langues

L'interface est disponible en cinq langues :

- français (par défaut)
- anglais
- espagnol
- allemand
- portugais

Changement de langue :

```bash
sudo respinguy --lang
```

ou menu principal > Paramètres et info > Langue.

Le choix est mémorisé dans `/usr/share/ResPinGuy-File-Config/respinguy-config.local`
(`RPG_LANG`). Surcharge ponctuelle :

```bash
sudo -E RPG_LANG=en respinguy
```

Les fichiers de traduction se trouvent dans `/usr/share/ResPinGuy-File/lang/`.
Une clé absente d'une traduction retombe automatiquement sur le français.


### Souris

La souris est prise en charge dans le **menu texte** (`RPG_UI_ENGINE=basic`) :

- clic gauche sur une entrée pour la sélectionner ;
- clic sur la ligne `q)` pour revenir ou quitter.

Pendant l'affichage du menu, le terminal capture la souris (la sélection de texte
à la souris est donc désactivée). Pour la retrouver :

```bash
sudo RPG_UI_ENGINE=basic RPG_NO_MOUSE=1 respinguy
```

`whiptail`/newt ne permet pas d'activer la souris de façon fiable.
`dialog`, s'il est installé, la gère nativement (`RPG_UI_ENGINE=dialog`).


### Compatibilité de démarrage

L'ISO générée est hybride :

- **BIOS** via isolinux ;
- **UEFI** via GRUB (si les outils UEFI sont installés) ;
- démarrage depuis **CD/DVD** ou **clé USB** (écriture avec `dd`).

Le démarrage utilise le **label de l'ISO** (`root=live:CDLABEL=...`) et non
`/dev/sr0` : il fonctionne même si le lecteur n'est pas `sr0`, et depuis une
clé USB.

Réglages de compatibilité appliqués au live :

- `selinux=0` et `apparmor=0` (évite les blocages liés aux labels du système source) ;
- overlayfs pour la couche inscriptible ;
- `/etc/fstab` et `/etc/crypttab` du système source neutralisés ;
- services réseau et plymouth bloquants masqués.

Distributions prévues pour la création : Debian/Ubuntu et dérivés,
Fedora/RHEL/CentOS et dérivés, openSUSE, Arch/Manjaro/CachyOS et dérivés,
Gentoo. LFS fonctionne si `dracut` (module `dmsquash-live`), `squashfs-tools`,
`xorriso`, GRUB EFI, `dosfstools` et `mtools` sont installés.

Limites physiques :

- **Secure Boot** doit être désactivé : le GRUB généré n'est pas signé.
- Les pilotes sont ceux du **noyau du système source**. Un noyau de distribution
  standard couvre la plupart du matériel, mais les pilotes propriétaires
  (NVIDIA, etc.) et certains firmwares doivent être installés sur la source
  avant de créer l'ISO.
- Une ISO créée sur une distribution reste une copie de **cette** distribution ;
  elle ne devient pas une ISO Debian ou Fedora.


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