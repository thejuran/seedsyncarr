import { Pipe, PipeTransform } from "@angular/core";

/*
 * Convert bytes into largest possible unit.
 * Takes an precision argument that defaults to 2.
 * Usage:
 *   bytes | fileSize:precision
 * Example:
 *   {{ 1024 |  fileSize}}
 *   formats to: 1 KB
 * Source: https://gist.github.com/JonCatmull/ecdf9441aaa37
 *         336d9ae2c7f9cb7289a#file-file-size-pipe-ts
*/
@Pipe({name: "fileSize", standalone: true})
export class FileSizePipe implements PipeTransform {

  private units = [
    "B",
    "KB",
    "MB",
    "GB",
    "TB",
    "PB"
  ];

  transform(bytes: number | null | undefined = 0, precision: number = 2, part?: "value" | "unit" ): string {
    if (bytes == null) { bytes = 0; }
    if ( isNaN( parseFloat( String(bytes) )) || ! isFinite( bytes ) ) { return "?"; }

    let unit = 0;

    while ( bytes >= 1024 && unit < this.units.length - 1 ) {
      bytes /= 1024;
      unit ++;
    }

    const safePrecision = Math.max(1, +precision);
    const val = Number(bytes.toPrecision(safePrecision));
    if (part === "value") { return String(val); }
    if (part === "unit") { return this.units[ unit ]; }
    return val + " " + this.units[ unit ];
  }
}
