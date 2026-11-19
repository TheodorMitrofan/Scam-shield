import { Pipe, PipeTransform, inject } from '@angular/core';
import { UiLang } from './ui-lang';

/**
 * Whole-UI RO/EN: `{{ 'Setul de validare' | ui }}`. The Romanian text is the key (and the fallback), so a
 * missing entry just stays Romanian. Impure on purpose: it re-renders when the RO|EN toggle changes.
 * Not translated on purpose: the received messages (evidence) and the police complaint (PDF / e-mail).
 */
@Pipe({ name: 'ui', pure: false })
export class UiPipe implements PipeTransform {
  private readonly lang = inject(UiLang);

  transform(ro: string | null | undefined): string {
    if (!ro) return '';
    return this.lang.lang() === 'en' ? (EN[ro] ?? ro) : ro;
  }
}

export const EN: Record<string, string> = {
  // top bar
  'Mesaje': 'Messages',
  'Secțiune': 'Section',
  'Schimbă tema': 'Change theme',
  'Temă deschisă': 'Light theme',
  'Temă întunecată': 'Dark theme',
  'Limba avertismentelor / Warning language': 'Language',
  'Limba': 'Language',
  'Doar dacă bifați, conversațiile verificate se păstrează (le puteți șterge oricând).':
    'Only if you switch this on are checked conversations kept (you can delete them any time).',
  'Salvează în istoric': 'Save to history',
  'Setul de validare': 'Validation set',
  'Fișiere JSON': 'JSON files',
  'Folder': 'Folder',
  'Lipește mesaj': 'Paste message',
  'Detector activ': 'Detector on',
  'Detector demo': 'Demo detector',
  'Server oprit': 'Server down',
  'Totul funcționează.': 'Everything works.',

  // channels
  'SMS': 'SMS',
  'WhatsApp': 'WhatsApp',
  'E-mail': 'E-mail',
  'Chat': 'Chat',
  'Apel telefonic': 'Phone call',
  'Toate canalele': 'All channels',

  // verdicts / filters / groups
  'Pare o țeapă! Nu răspundeți': 'Looks like a scam! Do not reply',
  'Atenție, verificați înainte să răspundeți': 'Careful, check before you reply',
  'Pare în regulă': 'Looks fine',
  'Toate': 'All',
  'Scam': 'Scam',
  'Suspect': 'Suspicious',
  'Sigur': 'Safe',

  // inbox list
  'Caută...': 'Search...',
  'Caută în mesaje': 'Search messages',
  'Filtrează după canal': 'Filter by channel',
  'Disponibil după analiză': 'Available after the check',
  'Selectează toate': 'Select all',
  'Marchează ca citite': 'Mark as read',
  'Șterge selecția din listă': 'Remove selection from the list',
  'Șterge din listă': 'Remove from the list',
  'Reîncearcă': 'Try again',
  'Se analizează': 'Checking',
  'necitit': 'unread',
  'Niciun scenariu nu se potrivește filtrelor.': 'No scenario matches the filters.',
  'Încărcați setul de validare, fișiere JSON sau lipiți un mesaj.': 'Load the validation set, JSON files or paste a message.',
  'Puteți trage fișierele direct în pagină.': 'You can drag the files straight onto the page.',
  'Mesajul nu a putut fi verificat acum.': 'The message could not be checked right now.',

  // scenario detail
  'Înapoi la listă': 'Back to the list',
  'Scenariul': 'Scenario',
  'Marchează ca necitit': 'Mark as unread',
  'Se analizează mesajul…': 'Checking the message…',
  'Raportează frauda': 'Report the fraud',
  'Pregătim noi sesizarea; dumneavoastră completați doar datele personale.':
    'We prepare the complaint; you only fill in your personal details.',
  'Alegeți o conversație din listă ca s-o vedeți aici.': 'Pick a conversation from the list to see it here.',

  // conversation views
  '✓ În agendă': '✓ In contacts',
  '⚠ Nu e în agendă': '⚠ Not in contacts',
  '⚠ Expeditor necunoscut': '⚠ Unknown sender',
  '⚠ Număr necunoscut': '⚠ Unknown number',
  'Dumneavoastră': 'You',
  'Dumneavoastră:': 'You:',
  'Apelantul': 'Caller',
  'Conversația nu are mesaje.': 'The conversation has no messages.',
  'Căsuța de e-mail': 'Mailbox',
  'către: dumneavoastră': 'to: you',
  'către:': 'to:',
  'adresă necunoscută': 'unknown address',
  'Necunoscut': 'Unknown',
  'Număr ascuns': 'Hidden number',
  'Apel — transcriere': 'Call — transcript',
  'Mesaj vocal': 'Voice message',
  'Regiune estimată din voce:': 'Region estimated from the voice:',
  '(mesaj gol)': '(empty message)',
  '(e-mail gol)': '(empty e-mail)',
  '(liniște)': '(silence)',

  // paste dialog
  'Verificați un mesaj sau o conversație': 'Check a message or a conversation',
  'De unde vine mesajul?': 'Where does the message come from?',
  'Nume expeditor (opțional)': 'Sender name (optional)',
  'Ex.: BancaDunarea': 'E.g.: BancaDunarea',
  'Adresa de e-mail': 'E-mail address',
  'Numărul de telefon': 'Phone number',
  '(opțional)': '(optional)',
  'Expeditorul este salvat în agendă': 'The sender is saved in my contacts',
  'Mesajul sau conversația': 'The message or the conversation',
  'Apăsați ca să schimbați cine a scris': 'Click to change who wrote it',
  'Răspunsul…': 'The reply…',
  'Lipiți e-mailul aici…': 'Paste the e-mail here…',
  'Scrieți sau lipiți mesajul…': 'Type or paste the message…',
  'Eu': 'Me',
  'Expeditor': 'Sender',
  'Previzualizare': 'Preview',
  'Inversează': 'Swap',
  'Schimbă cine e expeditorul și cine sunteți dumneavoastră': 'Swap who is the sender and who you are',
  'Aici vedeți mesajul așa cum arată în aplicație.': 'Here you see the message as it looks in the app.',
  'Renunță': 'Cancel',
  'Verifică': 'Check',
  'Enter trece la următorul mesaj, de la celălalt vorbitor. Shift+Enter face un rând nou în același mesaj. Apăsați pe eticheta din stânga ca să schimbați cine a scris.':
    'Enter moves to the next message, from the other person. Shift+Enter adds a new line in the same message. Click the label on the left to change who wrote it.',

  // dashboard
  'Sumar rezultate': 'Results summary',
  'Încărcate': 'Loaded',
  'În analiză': 'Checking',
  'Export CSV': 'Export CSV',
  'Tablou rezultate': 'Results table',
  'Se analizează…': 'Checking…',
  'Încărcați setul de validare, un folder cu scenarii JSON sau lipiți un mesaj.':
    'Load the validation set, a folder of JSON scenarios or paste a message.',

  // report dialog (UI only — the complaint itself stays Romanian, it is for the Romanian police)
  'Se pregătește raportul…': 'Preparing the report…',
  'Raportul a fost trimis': 'The report was sent',
  'L-am trimis pe e-mail către': 'We e-mailed it to',
  ', cu sesizarea în format PDF atașată.': ', with the complaint attached as a PDF.',
  'Închide': 'Close',
  'Nu ați greșit cu nimic. Am pregătit plângerea despre ce s-a întâmplat; completați datele dumneavoastră (câmpurile cu * sunt obligatorii) și apăsați Trimite e-mail.':
    'You did nothing wrong. We prepared the complaint about what happened; fill in your details (fields with * are required) and press Send e-mail.',
  'Datele dumneavoastră': 'Your details',
  'Completați câmpurile obligatorii:': 'Please fill in the required fields:',
  'Ce s-a întâmplat': 'What happened',
  'completat automat': 'filled in automatically',
  'Ce a folosit expeditorul': 'What the sender used',
  'Adresele sunt scrise „dezactivat” ([.] în loc de punct), ca să nu fie accesate.':
    'Addresses are written „disabled” ([.] instead of a dot) so they cannot be opened.',
  'Conversația': 'The conversation',
  'Se trimite la:': 'Will be sent to:',
  'Descarcă PDF': 'Download PDF',
  'Trimite e-mail': 'Send e-mail',
  'obligatoriu': 'required',
  'A apărut o eroare. Încercați din nou.': 'Something went wrong. Please try again.',
  'Adresă de internet': 'Web address',
  'Adresă de e-mail': 'E-mail address',
  'Telefon': 'Phone',
  'Cont (IBAN)': 'Account (IBAN)',
  'Sumă': 'Amount',
  // personal-data form (labels come from the backend)
  'Nume': 'Last name',
  'Prenume': 'First name',
  'CNP': 'Personal ID number (CNP)',
  '13 cifre': '13 digits',
  'Seria și numărul actului de identitate': 'ID card series and number',
  'Ex.: RX 123456': 'E.g.: RX 123456',
  'Adresa de domiciliu': 'Home address',
  'Localitate, stradă, nr., bloc, scară, etaj, ap., județ / sector':
    'Town, street, no., building, entrance, floor, flat, county / sector',
  'Ex.: 0722 123 456': 'E.g.: 0722 123 456',
  'Data la care ați primit mesajul': 'Date you received the message',
  'Ora aproximativă': 'Approximate time',
  'Am pierdut bani': 'I lost money',
  'Suma pierdută (lei)': 'Amount lost (lei)',
  'Banca dumneavoastră': 'Your bank',
  'Alte detalii': 'Other details',

  // audio — „Nepotul e în Spania?” card
  '„Nepotul e în Spania?” — verificăm locul declarat': '“Is the grandson in Spain?” — checking the claimed place',
  'SIMULAT': 'SIMULATED',
  'Escrocul spune că e în altă țară. Din avioanele care se aud în fundalul mesajului vocal și din ora mesajului verificăm dacă locul declarat se potrivește cu sunetul.':
    'The scammer says he is in another country. From the aircraft heard behind the voice message and the time of the message we check whether the claimed place matches the sound.',
  'Analizăm mesajul vocal…': 'Analysing the voice message…',
  'Serviciul audio nu răspunde. Porniți-l pe portul 8002.': 'The audio service is not responding. Start it on port 8002.',
  'număr necunoscut': 'unknown number',
  'Ce spune:': 'What he says:',
  'Nu putem verifica locul': 'We cannot check the place',
  'Spune că este în': 'Says he is in',
  'Sunetul se potrivește cu acest loc.': 'The sound matches this place.',
  'Sunetul NU se potrivește cu acest loc.': 'The sound does NOT match this place.',
  'Sunetul se potrivește cu': 'The sound matches',
  'niciun loc verificat': 'none of the places checked',
  'Ce să faceți:': 'What to do:',
  'nu trimiteți bani. Sunați-l pe nepot la numărul lui vechi, pe care îl cunoașteți.':
    'do not send money. Call your grandson on his old number, the one you know.',
  'Nu arătăm unde se află persoana, doar dacă sunetul se potrivește cu locul pe care îl declară. Detaliile tehnice pot fi anexate plângerii către poliție.':
    'We do not show where the person is, only whether the sound matches the place they claim. The technical details can be attached to the complaint to the police.',
  'Detalii tehnice': 'Technical details',
  'Ascunde detaliile tehnice': 'Hide technical details',
  'Madrid, Spania': 'Madrid, Spain',
  'Barcelona, Spania': 'Barcelona, Spain',
  'Paris, Franța': 'Paris, France',
  'Milano, Italia': 'Milan, Italy',
  'Roma, Italia': 'Rome, Italy',
  'Londra, Marea Britanie': 'London, United Kingdom',
  'Berlin, Germania': 'Berlin, Germany',
  'Viena, Austria': 'Vienna, Austria',
  'București, zona Aeroportului Băneasa': 'Bucharest, Băneasa Airport area',
};
