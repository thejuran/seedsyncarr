import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { OptionComponent, OptionType } from './option.component';

describe('OptionComponent', () => {
  let component: OptionComponent;
  let fixture: ComponentFixture<OptionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OptionComponent, FormsModule],
    }).compileComponents();
    fixture = TestBed.createComponent(OptionComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Checkbox type (toggle switch)', () => {
    beforeEach(() => {
      component.type = OptionType.Checkbox;
      component.label = 'Test Toggle';
      component.value = false;
      fixture.detectChanges();
    });

    it('should render toggle-track element for checkbox type', () => {
      const el = fixture.nativeElement.querySelector('.toggle-track');
      expect(el).toBeTruthy();
    });

    it('should render hidden checkbox input with toggle-input class', () => {
      const input = fixture.nativeElement.querySelector('input.toggle-input[type="checkbox"]');
      expect(input).toBeTruthy();
    });

    it('should NOT render form-check class', () => {
      const el = fixture.nativeElement.querySelector('.form-check');
      expect(el).toBeFalsy();
    });

    it('should bind ngModel to value input', () => {
      const input: HTMLInputElement = fixture.nativeElement.querySelector('input.toggle-input');
      expect(input.checked).toBe(false);
    });
  });
});
