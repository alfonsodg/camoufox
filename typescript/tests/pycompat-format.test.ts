/** formatPyG against f"{x:g}" as CPython printed it (python 3.14). */
import { expect, it } from "vitest";
import { formatPyG } from "../src/pycompat.js";

it.each([
	[1, "1"],
	[2.5, "2.5"],
	[1.0909090909, "1.09091"],
	[1.25, "1.25"],
	[0.00001234, "1.234e-05"],
	[0.0001, "0.0001"],
	[123456, "123456"],
	[1234567, "1.23457e+06"],
	[999999.5, "1e+06"],
	[1e21, "1e+21"],
	[0.1 + 0.2, "0.3"],
	[1396.3636363, "1396.36"],
	[3200, "3200"],
	[100000.4, "100000"],
])("formats %s as %s", (value, expected) => {
	expect(formatPyG(value)).toBe(expected);
});
