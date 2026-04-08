import { Pipe, PipeTransform } from "@angular/core";

/**
 * Pure pipe that checks if a file name is in the selected files set.
 *
 * This is more efficient than using a method call in the template because
 * Angular's pure pipe memoization means the transform is only called when
 * the input values actually change (reference comparison).
 *
 * Usage: [bulkSelected]="file.name | isSelected:selectedFiles"
 */
@Pipe({name: "isSelected", standalone: true, pure: true})
export class IsSelectedPipe implements PipeTransform {

    /**
     * Check if a file name is in the selected files set.
     * @param fileName The name of the file to check
     * @param selectedFiles The set of selected file names
     * @returns true if the file is selected, false otherwise
     */
    transform(fileName: string, selectedFiles: Set<string>): boolean {
        if (!fileName || !selectedFiles) {
            return false;
        }
        return selectedFiles.has(fileName);
    }

}
