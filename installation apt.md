Voici les problèmes que j'ai rencontré pour l'installation : "https://benoitlx.github.io/Documentation-Stage-G1/Technique/Installation"

installer le module "apt_interface-0.1.0-py3-none-any.whl" grâce à la commande "```pip install -i https://test.pypi.org/simple/ apt-interface```"
il faut enlever l'espace déjà, puis j'ai eu entre autres cette erreur : 

```
The Meson build system
      Version: 1.7.0
      Source dir: C:\Users\stris\AppData\Local\Temp\pip-install-_gszxgkz\matplotlib_86058baef8ac47158fe4b9103a94ca23
      Build dir: C:\Users\stris\AppData\Local\Temp\pip-install-_gszxgkz\matplotlib_86058baef8ac47158fe4b9103a94ca23\.mesonpy-erq3jkf6
      Build type: native build
      Program python3 found: YES
      Project name: matplotlib
      Project version: 3.10.0
      WARNING: Failed to activate VS environment: Could not parse vswhere.exe output
```
j'ai donc installé visual studio (différent de visual studio code) mais : 
  ```
Need python for x86_64, but found x86
```
  installer la bonne version **86_64 de python et ADD_TO_PATH très important** puis 
  ```
  python -m pip install C:\Path\to\apt_interface-0.1.0-py3-none-any.whl
```
Créer le fichier config_devicename.yaml et mettre un exemple de code dedans. 
