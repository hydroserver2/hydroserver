import { Subject } from 'rxjs'

export const DEFAULT_SNACK_DURATION = 3000

enum SnackType {
  Warning = 'Warning',
  Success = 'Success',
  Error = 'Error',
  Info = 'Info',
}

export enum SnackColor {
  Warning = 'warning',
  Success = 'success',
  Error = 'error',
  Info = 'info',
}

export enum SnackIcon {
  Success = 'mdi-checkbox-marked-circle',
  Warning = 'mdi-alert',
  Error = 'mdi-alert-circle',
  Info = 'mdi-information',
  None = 'none',
}

export enum SnackTitle {
  Warning = 'Warning',
  Success = 'Success',
  Error = 'Error',
  Info = 'Info',
}

export enum Position {
  Center = 'center',
  Left = 'left',
  Right = 'right',
  Bottom = 'bottom',
  Top = 'top',
}

export class Snack {
  constructor(
    public message: string = '',
    public color: SnackColor = SnackColor.Info,
    public icon: SnackIcon = SnackIcon.None,
    public title: SnackTitle = SnackTitle.Info,
    public timeout: number = DEFAULT_SNACK_DURATION,
    public position: Position = Position.Center,
    public visible: boolean = false
  ) {}
}

export class Snackbar {
  private static subject = new Subject<Snack>()

  static get snack$() {
    return this.subject.asObservable()
  }

  private static createSnackbar(message: string, type: SnackType): void {
    this.subject.next(
      new Snack(
        message,
        SnackColor[type],
        SnackIcon[type],
        SnackTitle[type],
        DEFAULT_SNACK_DURATION,
        Position.Bottom,
        true
      )
    )
  }

  static success(message: string): void {
    this.createSnackbar(message, SnackType.Success)
  }

  static warn(message: string): void {
    this.createSnackbar(message, SnackType.Warning)
  }

  static error(message: string): void {
    this.createSnackbar(message, SnackType.Error)
  }

  static info(message: string): void {
    this.createSnackbar(message, SnackType.Info)
  }
}
