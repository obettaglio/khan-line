// Creating a class and student roster

function showAddStudentForm(result) {
    // flash success message,
    // disable create-class-submit,
    // display add-student-header and add-student-form

    console.dir(result);
    $('#flash-msgs').append("<h3 class='msg'>Created class.</h3>");
    setTimeout(function() {
        $('.msg').remove();
    }, 2000);

    $('#create-class-submit').css('visibility', 'hidden');
    $('#add-student-header').css('visibility', 'visible');
    $('#add-student-form').css('visibility', 'visible');
}

function getClassInfo(evt) {
    // prevent submit button from redirecting,
    // send data to route via post request,
    // call showAddStudentForm

    evt.preventDefault();

    var formInputs = {
        "class-name": $("#class-name-field").val(),
        "subject": $("#subject-field").val()
    };

    $.post("/create-class",  // post route
           formInputs,
           showAddStudentForm
           );
}

function resetAddStudentForm(result) {
    // flash success message,
    // clear add-student-form

    console.dir(result);
    $('#flash-msgs').append("<h3 class='msg'>Added student.</h3>");
    setTimeout(function() {
        $('.msg').remove();
    }, 2000);

    $('#complete-class').css('visibility', 'visible');

    $('#f-name-field').val('');
    $('#l-name-field').val('');
    $('#student-email-field').val('');
    $('#khan-username-field').val('');
}

function getStudentInfo(evt) {
    // prevent submit button from redirecting,
    // send data to route via post request,
    // call resetAddStudentForm

    evt.preventDefault();

    var formInputs = {
        "f-name": $("#f-name-field").val(),
        "l-name": $("#l-name-field").val(),
        "student-email": $("#student-email-field").val(),
        "khan-username": $("#khan-username-field").val()
    };

    $.post("/add-student",  // post route
           formInputs,
           resetAddStudentForm
           );
}


$('#create-class-submit').on('click', getClassInfo);
$('#add-student-submit').on('click', getStudentInfo);