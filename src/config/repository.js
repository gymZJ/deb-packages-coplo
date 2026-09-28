function repositoryRoot() {
  return typeof window === 'undefined' ? '/' : new URL('/', window.location.origin).href
}

const root = repositoryRoot()

export const repository = Object.freeze({
  url: root,
  catalogUrl: new URL('catalog.json', root).href,
  keyUrl: new URL('coplo-archive-keyring.gpg', root).href,
  fingerprint: '07BE A666 9ADC AD3D F544 4CDF ED0A 83D3 BD2F E143',
  component: 'main',
})

export function repositorySetupCommand(suite) {
  return `sudo mkdir -p /etc/apt/keyrings
curl -fsSL ${repository.keyUrl} \\
  | sudo tee /etc/apt/keyrings/coplo-archive-keyring.gpg >/dev/null

sudo tee /etc/apt/sources.list.d/coplo.sources >/dev/null <<'EOF'
Types: deb
URIs: ${repository.url}
Suites: ${suite}
Components: ${repository.component}
Signed-By: /etc/apt/keyrings/coplo-archive-keyring.gpg
EOF

sudo apt update`
}
