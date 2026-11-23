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


### Interface interactive

La commande `respinguy` ouvre un menu plein écran :

```bash
sudo respinguy
```

Actions disponibles :
- Créer l'image ISO (avec un résumé avant lancement)
- Configuration (nom, dossier de sortie, home, kernel, dossiers inclus)
- Vérification et installation des dépendances
- Mise à jour et suppression de ResPinGuy

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

ou menu principal > Langue.

Le choix est mémorisé dans `/usr/share/ResPinGuy-File-Config/respinguy-config.local`
(`RPG_LANG`). Surcharge ponctuelle :

```bash
sudo -E RPG_LANG=en respinguy
```

Les fichiers de traduction se trouvent dans `/usr/share/ResPinGuy-File/lang/`.
Une clé absente d'une traduction retombe automatiquement sur le français.


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

&copy; 2023 [ResPinGuy](https://respinguy.fopg.fr/)