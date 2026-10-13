// These Vite namespaces bypass customLogger and include raw request URLs.
export function protectedDevelopmentEnvironment(environment) {
  const exclusions = ['-vite:proxy', '-vite:time'];
  const diagnostics = (environment.DEBUG ?? '').split(/[\s,]+/)
    .filter((entry) => entry && !exclusions.includes(entry));
  return { ...environment, DEBUG: [...diagnostics, ...exclusions].join(',') };
}
