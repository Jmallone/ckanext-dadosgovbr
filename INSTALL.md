# Instalação do ckanext-dadosgovbr

## Compatibilidade

Este plugin foi atualizado para ser compatível com:
- CKAN 2.9+
- Python 3.6+
- Flask (substituindo Pylons)

## Instalação

### 1. Ativar o ambiente virtual (se aplicável)
```bash
source /path/to/your/ckan/venv/bin/activate
```

### 2. Instalar o plugin
```bash
pip install -e .
```

### 3. Configurar o plugin
Adicione o plugin à configuração do CKAN (`production.ini` ou `development.ini`):

```ini
[app:main]
ckan.plugins = ... dadosgovbr
```

### 4. Configurações específicas (opcional)
Para funcionalidades específicas, adicione ao arquivo de configuração:

```ini
## E-Ouv
eouv.url  = http://URL_DA_OUVIDORIA_AQUI.gov.br
eouv.user = USUARIO_AQUI
eouv.pass = SENHA_AQUI
```

## Principais mudanças de compatibilidade

### APIs removidas/substituídas:
- `c`, `g`, `h` de `ckan.lib.base` → `toolkit.g`, `toolkit.h`
- `pylons.controllers.util.redirect` → `flask.redirect`
- `pylons.request` → `flask.request`
- `unicode()` → `str()`
- `.decode('utf-8')` → remoção (não necessário em Python 3)

### Sintaxe atualizada:
- `implements()` → `plugins.implements()`
- `request.GET` → `request.args`
- `render()` → `toolkit.render()`

## Solução de problemas

### Erro de importação
Se encontrar erros de importação, verifique se todas as dependências estão instaladas:
```bash
pip install -r requirements.txt
```

### Erro de compatibilidade
Se ainda houver problemas de compatibilidade, verifique:
1. Versão do CKAN instalada
2. Versão do Python
3. Se todas as dependências estão atualizadas

## Desenvolvimento

Para desenvolvimento, instale as dependências de desenvolvimento:
```bash
pip install -r requirements.txt
pip install -e .[dev]
``` 