import redos from "redos";
import { readFile, writeFile } from "fs/promises";
import cliProgress from "cli-progress";
async function main() {
  const unsafePatterns = [];

  const data = await readFile("../tmp/output_4.json");
  const regexObjects = JSON.parse(data);

  const progressBar = new cliProgress.SingleBar(
    {},
    cliProgress.Presets.shades_classic
  );
  let counter = 0;
  progressBar.start(regexObjects.length, 0);
  for (let regexObject of regexObjects) {
    progressBar.update(counter);
    try {
      redos(regexObject.pattern, (nodes) => {
        for (let resultObject of nodes.results()) {
          if (!resultObject.safe) {
            unsafePatterns.push(regexObject.pattern);
          }
        }
      });
    } catch (error) {
      continue;
    }
    counter++;
  }

  await writeFile("./unsafe-regexes.json", JSON.stringify(unsafePatterns));
  progressBar.stop();
}

main();
