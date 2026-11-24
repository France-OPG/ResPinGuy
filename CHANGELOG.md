# Journal des modifications

Toutes les modifications notables de ResPinGuy sont consignées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).
Les entrées les plus récentes sont en haut.

## [0.32] - 2026-11-24

### Ajouté
- Numéro de version affiché en haut à droite de l'interface (au format `0.32`).
- Fichier `ResPinGuy-File/VERSION` : source unique du numéro de version.

## [0.31] - 2026-11-23

### Ajouté
- Interface texte (TUI) lancée par `respinguy` : accueil, build, configuration,
  dépendances, mise à jour, suppression, aide.
- Interface multilingue : français (par défaut), anglais, espagnol, allemand,
  portugais. Choix via le menu principal ou `respinguy --lang`, mémorisé dans
  `respinguy-config.local` (`RPG_LANG`). Traductions dans `ResPinGuy-File/lang/`.
- Interface adaptative : la hauteur et la largeur des écrans sont recalculées
  à chaque affichage, y compris après un redimensionnement du terminal.
- Palette de l'interface :
  fond noir, texte jaune `#ffb516`, cadre bleu `#1d2f52`.
  Sélection : texte jaune sur fond vert `#73ba25`.
  Boutons Valider/Quitter : texte jaune sur fond rouge `#ee0000`.
  « ResPinGuy » est affiché à gauche.
  Thème whiptail (couleurs terminal approchantes) et équivalent ANSI truecolor
  exact pour le menu texte.
- Redimensionnement : le menu texte détecte la taille toutes les 250 ms et se
  redessine immédiatement. Les écrans whiptail reprennent la nouvelle taille
  au prochain écran (limite de newt). `RPG_UI_ENGINE=basic` force le menu texte.
- Thème « danger » (rouge) pour les actions destructives et les erreurs.
- Souris dans le menu texte : clic gauche pour sélectionner une entrée, clic
  sur `q)` pour revenir. Désactivable avec `RPG_NO_MOUSE=1`.
- ISO hybrides **BIOS + UEFI** (GRUB EFI) quand les outils UEFI sont présents.
- Démarrage par **label ISO** (`root=live:CDLABEL=...`) : CD/DVD et clé USB,
  sans dépendre de `/dev/sr0`.
- Réglages de compatibilité live : `selinux=0`, `apparmor=0`, overlayfs,
  `/etc/crypttab` neutralisé.
- Détection des outils UEFI (`grub-mkstandalone`/`grub2-mkstandalone`,
  `dosfstools`, `mtools`) avec repli BIOS s'ils sont absents.
- Installateur live (`respinguy-install` + entrée TUI) : disque entier, GPT/MBR,
  ext4, GRUB, restauration du `/etc` d'origine, initramfs, mots de passe.
- `respinguy-build` : archive `LiveOS/etc-original.tar` pour l'installateur et
  exclusion de `/boot/efi` du squashfs.
- Accès direct : `respinguy --build`, `--config`, `--deps`, `--help`.
- Moteur d'affichage : `whiptail`, sinon `dialog`, sinon menu texte simple
  (aucune nouvelle dépendance obligatoire).
- Fichier `respinguy-config.local` : réglages enregistrés par l'interface,
  prioritaires sur `respinguy-config`.
- Migration automatique des anciennes configurations : ajout de deux lignes de
  compatibilité, sans écraser la configuration existante.
- `.gitattributes` : fins de ligne LF forcées (développement sous Windows).
- Section « Interface interactive » dans la documentation.

### Modifié
- `respinguy-build` : menus BIOS et UEFI générés avec le label ISO ; xorriso
  produit une image hybride (El Torito EFI + GPT) quand l'UEFI est disponible.
- Accueil simplifié : dépendances, mise à jour, suppression, langue et aide
  sont regroupées dans un sous-menu « Paramètres et info ».
- `ResPinGuy-File/respinguy` : la simple liste d'aide est remplacée par la TUI.
- `ResPinGuy-CMD/respinguy` : transmet les arguments à la TUI.
- `ResPinGuy-CMD/respinguy-config` : ouvre la page Configuration de la TUI.
- `ResPinGuy-File-Config/respinguy-config` : détection du kernel factorisée,
  prise en charge des surcharges locales, vérification de
  `RPGCONFIGUSER` / `RPGCONFIGUSERPERS`.
- `install`, `ResPinGuy-File/respinguy-app-up`, `ResPinGuy-File/respinguy-app-rm` :
  7 commandes au lieu de 6.
- `ResPinGuy-File/respinguy-app-up` : supprime `/tmp/ResPinGuy` avant le clone.

### Corrigé
- Le dossier `/etc` du live était injecté depuis un dossier temporaire dont le
  nom n'était pas `etc` : le squashfs n'avait donc pas de `/etc` et le live ne
  pouvait pas démarrer. Le dossier temporaire est maintenant créé sous un chemin
  se terminant par `/etc`.
- `respinguy-config` éditait `respinguy-app-dep-force-install` au lieu du
  fichier de configuration.
- `respinguy-app-dep-force-install` n'était pas installée dans `/usr/bin`.
- `respinguy-app-up` échouait si `/tmp/ResPinGuy` existait déjà.
- Le dossier de sortie du build est maintenant validé : les dossiers système
  sont refusés, car le build exécute `rm -rf "$RPGHOME"`.

### Supprimé
- Mention « The Kompiler » retirée du README, de la documentation et de
  l'interface (nom du projet : ResPinGuy).

### Sécurité
- `update` et `remove` utilisent `exec` : le script courant ne continue pas à
  être lu pendant que ses fichiers sont remplacés ou supprimés.
