const frases = [

"El esfuerzo de hoy es el éxito de mañana.",

"Cada pregunta resuelta te acerca a tu meta.",

"Aprender es avanzar.",

"La constancia supera al talento.",

"Nunca subestimes una hora de estudio.",

"Tu futuro comienza con lo que haces hoy.",

"La disciplina vence a la motivación."

];

const numeroDia = new Date().getDay();

document.getElementById("frase").innerText =
frases[numeroDia];
