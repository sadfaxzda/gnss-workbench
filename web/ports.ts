// Separate local ports let tests coexist with other development applications.
function localPort(name: string, fallback: number): number {
  const value = Number(process.env[name] ?? fallback)
  if (!Number.isInteger(value) || value < 1024 || value > 65535) {
    throw new Error(`${name} must be an integer in 1024..65535`)
  }
  return value
}

export const apiPort = localPort('GNSS_API_PORT', 8000)
export const webPort = localPort('GNSS_WEB_PORT', 5173)
