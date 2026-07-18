import { main } from "./main.js";

process.exitCode = await main(process.argv.slice(2).length === 0 ? ["demo", "--offline"] : process.argv.slice(2));
