import {Component, Input, Output, ChangeDetectionStrategy, EventEmitter, OnInit, OnDestroy} from "@angular/core";

import {FormsModule} from "@angular/forms";
import {Subject} from "rxjs";
import {debounceTime, distinctUntilChanged, takeUntil} from "rxjs/operators";

@Component({
    selector: "app-option",
    providers: [],
    templateUrl: "./option.component.html",
    styleUrls: ["./option.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [FormsModule]
})
export class OptionComponent implements OnInit, OnDestroy {
    @Input() type!: OptionType;
    @Input() label!: string;
    @Input() value!: string | number | boolean;
    @Input() description!: string;
    @Input() compact = false;
    @Input() icon: string | null = null;

    @Output() changeEvent = new EventEmitter<string | number | boolean>();

    // expose to template
    public OptionType = OptionType;
    public passwordVisible = false;

    private readonly DEBOUNCE_TIME_MS: number = 1000;

    private newValue = new Subject<string | number | boolean>();
    private destroy$ = new Subject<void>();

    ngOnInit(): void {
        // Debounce
        // References:
        //      https://angular.io/tutorial/toh-pt6#fix-the-herosearchcomponent-class
        //      https://stackoverflow.com/a/41965515
        this.newValue
            .pipe(
                debounceTime(this.DEBOUNCE_TIME_MS),
                distinctUntilChanged(),
                takeUntil(this.destroy$)
            )
            .subscribe({next: val => this.changeEvent.emit(val)});
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    onChange(value: string | number | boolean): void {
        this.newValue.next(value);
    }
}

export enum OptionType {
    Text,
    Checkbox,
    Password
}
